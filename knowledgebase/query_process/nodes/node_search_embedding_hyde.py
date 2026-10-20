from langchain.chat_models import init_chat_model

from knowledgebase.config.config import LLMConfig, MilvusConfig
from knowledgebase.config.prompt import HYDE_PROMPT
from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger
from knowledgebase.tool.milvus_client_tool import get_search_reqs, hybrid_search
from knowledgebase.utils.embedding_utils import get_bge_embeddings

class NodeSearchEmbeddingHyde(NodeBase):
    """
    节点功能：HyDE (Hypothetical Document Embedding)
    先让 LLM 生成假设性答案，再对答案进行向量检索，提高召回率。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_search_embedding_hyde"

    def process(self, state: QueryGraphState):
        rewritten_query = state.get("rewritten_query")
        item_names = state.get("item_names")
        if not rewritten_query:
            logger.error("Rewritten query could not be empty")
            raise ValueError("Rewritten query could not be empty")

        if not item_names:
            logger.error("Item names could not be empty")
            raise ValueError("Item names could not be empty")

        # 先把重写的问题丢给大模型，让大模型生成假设性答案
        llm = init_chat_model(
            model=LLMConfig.item_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )

        messages = [
            {"role": "user", "content": HYDE_PROMPT.format(rewritten_query=rewritten_query)}
        ]

        res = llm.invoke(input=messages)
        hyde_answer = res.content
        print(hyde_answer)

        # 把重写的问题进行向量化
        embeddings = get_bge_embeddings([rewritten_query + "\n" + hyde_answer])
        dense_data = embeddings.get("dense")[0]
        sparse_data = embeddings.get("sparse")[0]

        # 混合检索
        # 导入模块我们做了主体识别，识别的item_name保存在milvus，这个节点的作用
        # 1. item_name保存起来再后续检索模块意图识别的时候，进行相似度匹配来确认用户问的商品milvus当中存在不存在
        # 2. 根据用户问题检索chunks的时候，chunks在导入模块也回填了主体识别的item_name,所以这里检索的时候，
        #    通过查看chunks的item_name是不是在确认的意图识别的item_names当中, 是就拿，不是不要
        expr = f"item_name in {json_format(item_names)}"
        
        reqs = get_search_reqs(
            dense_data=[dense_data],
            sparse_data=[sparse_data],
            dense_anns_field="dense_vector",
            sparse_anns_field="sparse_vector",
            expr=expr,
        )

        res = hybrid_search(
            collection_name=MilvusConfig.chunks_collection,
            reqs=reqs,
            output_fields=["id", "title", "file_title", "content", "part", "item_name"],
            ranker=(0.8, 0.2),
        )

        chunks = [
            {
                **item.get("entity"),
                "score": item.get("distance"),
                "source": "local",
            }
            for item in res[0]
        ]

        # return state
        return {"hyde_embedding_chunks": chunks}

if __name__ == "__main__":
    init_state = {
        "rewritten_query": "What kinds of Birth Flower Cufflinks?",
        "item_names": ["Birth Flower Cufflinks Gold Groom"]
    }
    node_search_embedding_hyde = NodeSearchEmbeddingHyde()
    result = node_search_embedding_hyde(init_state)
    logger.info(json_format(result))