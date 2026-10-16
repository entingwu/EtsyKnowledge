import json

from langchain.chat_models import init_chat_model

from knowledgebase.config.config import LLMConfig
from knowledgebase.config.prompt import ITEM_NAME_SYSTEM_PROMPT, ITEM_NAME_USER_PROMPT_TEMPLATE
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format


class NodeItemNameRecognition(NodeBase):
    """
    主体识别节点：主体识别与标签提取
    """

    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState):
        # 0. 获取数据
        chunks = state.get("chunks")
        file_title = state.get("file_title")
        if not chunks or not file_title:
            logger.error("chunks and title could not be empty.")
            raise ValueError("chunks and title could not be empty.")

        # 1. 拿到部分的chunk，把这些chunk的内容拼接起来变成一个字符串
        chunk_k_list = chunks[:15]
        chunks_str = ""
        max_length = 10000
        for idx, chunk in enumerate(chunk_k_list, start=1):
            title = chunk.get("title")
            content = chunk.get("content")
            chunk_text = f"[chunk{idx}\ntitle: {title}\ncontent: {content}]\n\n"
            # print(chunk_text)
            chunks_str += chunk_text
            if len(chunks_str) > max_length:
                break
        chunks_str = chunks_str[:max_length]

        # 2. 调用大模型把拼接的字符串作为prompt，整理总结主体（商品名）
        llm = init_chat_model(
            model=LLMConfig.item_model,
            model_provider="openai",
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature,
        )

        messages = [
            {"role": "system", "content": ITEM_NAME_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_USER_PROMPT_TEMPLATE.format(file_title=file_title, context=chunks_str)}
        ]
        res = llm.invoke(input=messages)
        item_name = res.content.replace("\n", "").replace("\t", "").replace(" ", "")
        if not item_name:
            item_name = file_title
        # 3. 把整理的商品名需要向量化，存储到milvus
        # 4. 把识别的商品名回填到每个chunk

        return state

if __name__ == '__main__':
    node = NodeItemNameRecognition()
    with open(r"/Users/entingwu/PycharmProjects/EtsyKnowledge/data/chunks.json", "r", encoding="utf-8") as f:
        # chunks = f.read()
        chunks = json.load(f)
    init_state = {
        # "chunks": json.loads(chunks)
        "chunks": chunks,
        "file_title": "001_4565343414_cufflinks-gold-groom"
    }
    result = node(init_state)
    # logger.info(json_format(result))