import json
from pathlib import Path

from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format
from knowledgebase.utils.embedding_utils import get_bge_embeddings


class NodeBGEEmbedding(NodeBase):
    """
    混合向量化节点：使用 BGE-M3 模型将文本转换为向量
    """

    name = "node_bge_embedding"

    def process(self, state: ImportGraphState):
        # 从state当中获取chunks
        chunks = state.get("chunks")
        if not chunks:
            logger.error("没有获取到chunks数据，没法进行向量化处理")
            raise ValueError("没有获取到chunks数据，没法进行向量化处理")
        # 对chunks进行向量化
        # bgem3在加载模型对象的时候有参数是可以做到批处理
        # get_bge_embeddings([f"{item.get('item_name')}\n{item.get('content')}" for item in chunks])
        
        # 自己手动实现批处理
        for i in range(0, len(chunks), 3):
            chunk_k_list = chunks[i: i + 3]
            print("@@", chunk_k_list)
            # 整理双向量化的字符串列表
            chunk_k_str_list = [f"{item.get('item_name')}\n{item.get('content')}" for item in chunk_k_list]
            print("@@@", chunk_k_str_list)
            embeddings = get_bge_embeddings(chunk_k_str_list)

            # 我们向量化结束主要就是把每个内容对应的向量回填到对应的chunk当中
            for idx, chunk in enumerate(chunk_k_list):
                chunk["dense_vector"] = embeddings.get("dense")[idx]
                chunk["sparse_vector"] = embeddings.get("sparse")[idx]

        with open(Path(__file__).resolve().parents[3] / "output/chunks_embedding.json", "w", encoding="utf-8") as f:
            f.write(json_format(chunks))
        return {
            "chunks": chunks
        }

if __name__ == "__main__":
    node = NodeBGEEmbedding()
    with open(Path(__file__).resolve().parents[3] / "output/chunk_item_name.json", "r", encoding="utf-8") as f:
        data = f.read() # 拿到的还是json串
    
    init_state = {
        "chunks": json.loads(data) # 反序列化
    }
    result = node(init_state)
    # logger.info(json_format(result))