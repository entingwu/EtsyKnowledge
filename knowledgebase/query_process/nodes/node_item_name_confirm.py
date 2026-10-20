import json

from langchain.chat_models import init_chat_model

from knowledgebase.config.config import LLMConfig, MilvusConfig
from knowledgebase.config.prompt import ITEM_NAME_EXTRACT_SYSTEM_PROMPT, ITEM_NAME_EXTRACT_TEMPLATE
from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger
from knowledgebase.tool.milvus_client_tool import get_search_reqs, hybrid_search
from knowledgebase.tool.mongo_tool import get_recent_messages, save_chat_message, update_history_item_names
from knowledgebase.utils.embedding_utils import get_bge_embeddings

class NodeItemNameConfirm(NodeBase):
    """
    节点功能：确认用户问题中的核心商品名称。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_item_name_confirm"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        # 1. 获取state给的初始化数据，查询mongo拿到历史记录整理成字符串
        original_query, session_id, message_id, history_str = self.get_history_str(state)

        # 2. 根据历史记录和原始问题，调用大模型提取商品名称和重写的问题
        item_names, rewritten_query = self.get_item_names(original_query, history_str)
        #item_names是大模型根据问题和历史记录给我们生成的名字，目前并不是咱们之前保存在milvus的名字
        
        #根据大模型生成的名字 向量化 从item_name表里面去找相似度
        final_item_names = []
        answer = "Sorry, we couldn't identify the product you're asking about. Please rephrase your question."
        if item_names:
            # 3. 向量化检索，遍历大模型给识别的商品名称，一个一个去混合检索milvus当中相似的item_names整理放在列表
            search_item_name_list = self.hybrid_search_item_names(item_names)

            # 4. 对齐商品名称，区分出确认的名字、可能的名字、噪音(最终的item_names保存在final_item_names中)
            answer, final_item_names = self.align_item_names(search_item_name_list)


        # 5. 处理历史记录，更新商品名称和重写问题到历史记录中
        message_id = self.handle_history(session_id, message_id, answer, final_item_names, rewritten_query)

        return {
            "message_id": message_id, # 保存最新添加的历史记录id
            "original_query": original_query,
            "answer": answer,
            "item_names": final_item_names,
            "rewritten_query": rewritten_query,
            "history": get_recent_messages(session_id), # 这里必须重新获取历史记录，否则拿到还是回填前
        }

    def hybrid_search_item_names(self, item_names):
        # 识别出来有item_names名字，然后我们再去向量化检索，名称对齐，否则没必要走这两步
        embeddings = get_bge_embeddings(item_names)
        search_item_name_list = []
        for idx, item_name in enumerate(item_names):
            dense_data = embeddings.get("dense")[idx]
            sparse_data = embeddings.get("sparse")[idx]

            # 混合检索
            reqs = get_search_reqs(
                dense_data=[dense_data], #
                dense_anns_field="dense_vector",
                sparse_data=[sparse_data],
                sparse_anns_field="sparse_vector",
            )
            res = hybrid_search(
                collection_name=MilvusConfig.item_name_collection,
                reqs=reqs,
                ranker=(0.8, 0.2), # (dense, sparse)
                output_fields=["item_name", "file_title"]
            )
            #print('$', json_format(res))
            
            if not res:
                continue
            # original_item_name: 识别的名字.
            # search_item_name: 在milvus找到的名字.
            for search_item_name_dict in res[0]:
                search_item_name_list.append({
                    "original_item_name": item_name,
                    "search_item_name": search_item_name_dict.get("entity", {}).get("item_name"),
                    "score": search_item_name_dict.get("distance", 0)
                })
        return search_item_name_list

    def align_item_names(self, search_item_name_list):
        # 把检索整理的结果进行商品名称对齐：就是区分出确认的名字、可能的名字、噪音
        confirm_item_names = [
            search_item_name.get("search_item_name") for search_item_name in search_item_name_list if search_item_name["score"] >= 0.85]

        option_item_names = [
            search_item_name.get("search_item_name") for search_item_name in search_item_name_list if search_item_name["score"] < 0.85
                                                                                                and search_item_name["score"] >= 0.6
        ]

        if confirm_item_names:
            # 有确定的名字
            final_item_names = confirm_item_names
            answer = ''
        elif option_item_names:
            # 没有确定的但是有可选的
            final_item_names = []
            answer = f"Which of these products are you asking about: {', '.join(option_item_names)}?"
        else:
            # 全是噪音，没有任何名字
            final_item_names = []
            answer = "Sorry, we couldn't identify the product you're asking about. Please rephrase your question."
        return answer, final_item_names

    def handle_history(self, session_id, message_id, answer, final_item_names, rewritten_query):
        # 把商品名称对齐完成后，其实这个节点主要功能就结束了，但是我们需要把历史记录处理一下。
        if answer:
            # 保存这个答案作为历史记录
            message_id = save_chat_message(
                session_id=session_id,
                role="assistant",
                text=answer,
            )
        history_list = get_recent_messages(session_id, n=10)
        history_ids = [history.get("_id") for history in history_list]
        update_history_item_names(ids=history_ids, item_names=final_item_names, rewritten_query=rewritten_query)
        return message_id

    def get_history_str(self, state: QueryGraphState):
        original_query = state.get("original_query")
        session_id = state.get("session_id")
        if not original_query:
            logger.error(f"Original question could not be empty")
            raise ValueError("Original question could not be empty")

        if not session_id:
            logger.error(f"Conversation id could not be empty")
            raise ValueError("Conversation id could not be empty")

        history_list = get_recent_messages(session_id)
        # 把当前这个用户的问题，立即保存历史记录
        message_id = save_chat_message(session_id, "user", original_query)

        # 把历史记录当中的role和text拼接起来，形成一个字符串，然后和原始问题一起交给大模型
        history_str = ''
        for history in reversed(history_list):
            role = history.get("role")
            text = history.get("text")
            history_str += f"{role}: {text}\n"
        return original_query, session_id, message_id, history_str

    def get_item_names(self, original_query, history_str):
        # 初始化大模型对象
        llm = init_chat_model(
            model=LLMConfig.llm_default_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )

        messages = [
            {"role": "system", "content": ITEM_NAME_EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_EXTRACT_TEMPLATE.format(history_text=history_str, original_query=original_query)}
        ]

        res = llm.invoke(input=messages)
        res_json = res.content
        res_data = json.loads(res_json)

        item_names = res_data.get("item_names", [])
        item_names = [item.replace("\n", "").replace("\t", "") for item in item_names]

        rewritten_query = res_data.get("rewritten_query", original_query)
        return item_names, rewritten_query


if __name__ == "__main__":
    # 模拟会话历史
    session_id = "test_001"
    save_chat_message(session_id, "user", "Please Introduce Birth Flower Cufflinks Gold Groom")
    save_chat_message(session_id, "assistant", "Hi, which one do you like?")
    save_chat_message(session_id, "user", "Birth Flower Cufflinks Gold Groom")
    save_chat_message(session_id, "assistant", "Any specific questions?")

    # 初始化图状态
    init_state = {
        "session_id": "test_001",
        "original_query": "How to use?"
    }

    # 创建节点对象
    node_item_name_confirm = NodeItemNameConfirm()
    # 执行节点的单元测试
    result = node_item_name_confirm(init_state)
    # 将返回的图状态进行json序列化
    logger.info(json_format(result))