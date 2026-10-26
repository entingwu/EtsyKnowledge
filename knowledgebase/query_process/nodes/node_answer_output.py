import re

from langchain.chat_models import init_chat_model

from knowledgebase.config.config import LLMConfig
from knowledgebase.config.prompt import ANSWER_PROMPT
from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.mongo_tool import save_chat_message
from knowledgebase.tool.task_utils import put_data

class NodeAnswerOutput(NodeBase):
    """
    节点功能: 答案生成
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_answer_output"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        task_id = state.get("task_id")
        answer = state.get("answer")
        if answer:
            # 1. 如果在意图识别的时候已经得到答案，直接放队列，后期sse推送到前端
            put_data(task_id, "final", {"answer": answer})
        else:
            # 2. 格式化提示词
            chunks, item_names, prompt, rewritten_query = self.format_prompt(state)

            # 3. 大模型生成答案，流式输出，推送到前端
            answer = self.generate_answer(prompt, task_id)

            # 4. 获取chunks当中图片url
            images = self.get_image_urls(chunks)

            # 5. 把答案写入历史记录并且推送图片
            self.write_history(answer, images, item_names, rewritten_query, state, task_id)

        return {
            "answer": answer,
        }

    def format_prompt(self, state: QueryGraphState):
        # 拿到切片内容拼接在一起
        chunks = state.get("reranked_docs") or []
        chunk_content = ""
        for idx, chunk in enumerate(chunks, start=1):
            title = chunk.get("title")
            content = chunk.get("content") or ""
            url = chunk.get("url")
            source = chunk.get("source")
            chunk_content += f"[{idx}][{source}][{title}][{url}]\n{content}\n\n"

        # 历史记录是按时间倒序查出来的，拼提示词时要按时间正序
        history = state.get("history") or []
        history_content = ""
        for h in reversed(history):
            history_content += f"[{h.get('role')}]: {h.get('text')}\n\n"

        item_names = state.get("item_names") or []
        rewritten_query = state.get("rewritten_query")
        prompt = ANSWER_PROMPT.format(
            context=chunk_content,
            history=history_content,
            item_names=", ".join(item_names),
            question=rewritten_query,
        )
        prompt = prompt[:12000]
        return chunks, item_names, prompt, rewritten_query

    def generate_answer(self, prompt, task_id):
        llm = init_chat_model(
            model=LLMConfig.llm_default_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )
        messages = [
            {"role": "user", "content": prompt}
        ]
        answer = ""  # 这个是完整的答案，要存储到state里面
        for msg in llm.stream(input=messages):
            # 流式输出，把答案放入队列，后续sse推送
            put_data(task_id, "delta", {"delta": msg.content})
            answer += msg.content
        return answer

    def get_image_urls(self, chunks):
        # 识别chunks当中图片url，去重并保持顺序
        # 图片文件名是内容哈希，不同listing共用的同一张照片url不同但文件名相同，所以按文件名去重
        images = []
        seen = set()
        md_img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        for chunk in chunks:
            for img_url in md_img_pattern.findall(chunk.get("content") or ""):
                img_url = img_url.strip()
                file_name = img_url.rsplit("/", 1)[-1]
                if img_url and file_name not in seen:
                    seen.add(file_name)
                    images.append(img_url)
        return images

    def write_history(self, answer, images, item_names, rewritten_query, state, task_id):
        # 需要把这个答案变为历史记录存储mongo
        if answer:
            save_chat_message(
                session_id=state.get("session_id"),
                role="assistant",
                text=answer,
                rewritten_query=rewritten_query,
                item_names=item_names,
                image_urls=images,
            )
        logger.info(f"答案生成完成，图片{len(images)}张")
        # final事件只带图片，前端用流式拼接的文本作为最终答案
        put_data(task_id, "final", {"image_urls": images})
