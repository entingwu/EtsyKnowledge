from knowledgebase.config.config import MilvusConfig
from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger
from knowledgebase.tool.milvus_client_tool import get_search_reqs, hybrid_search
from knowledgebase.utils.embedding_utils import get_bge_embeddings

class NodeSearchEmbedding(NodeBase):
     """
    节点功能：基于已确认主体名+改写后的用户问题，执行Milvus向量数据库混合检索
    """

     # 覆盖基类的 name 属性，标识节点名称
     name: str = "node_search_embedding"

     def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        rewritten_query = state.get("rewritten_query") # 让我们检索用的
        item_names = state.get("item_names") # 让我们在检索的时候过滤的条件

        # 把重写的问题进行向量化
        embeddings = get_bge_embeddings([rewritten_query])
        dense_data = embeddings.get("dense")[0]
        sparse_data = embeddings.get("sparse")[0]

        # 混合检索
        # 导入模块我们做了主体识别，识别的item_name保存在milvus，这个节点的作用
        # 1. item_name保存起来再后续检索模块意图识别的时候，进行相似度匹配来确认用户问的商品milvus当中存在不存在
        # 2. 根据用户问题检索chunks的时候，chunks在导入模块也回填了主体识别的item_name,所以这里检索的时候，
        #    通过查看chunks的item_name是不是在确认的意图识别的item_names当中, 是就拿，不是不要
        item_names = [
            item_name.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            for item_name in item_names
        ]
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
            ranker=(0.6, 0.4),
        )

        chunks = [
            {
                **item.get("entity"),
                "score": item.get("distance"),
                "source": "local",
            }
            for item in res[0]
        ]

        return {
            "embedding_chunks":  chunks
        }

if __name__ == "__main__":
     init_state = {
          "rewritten_query": "What kinds of Birth Flower Cufflinks?",
          "item_names": ["Birth Flower Cufflinks Gold Groom"]
     }
     node_search_embedding = NodeSearchEmbedding()
     result = node_search_embedding(init_state)
     logger.info(json_format(result))