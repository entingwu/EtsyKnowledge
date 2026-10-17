import json
from pathlib import Path

from pymilvus import DataType

from knowledgebase.config.config import MilvusConfig
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.milvus_client_tool import get_milvus_client


class NodeImportMilvus(NodeBase):
    """
    导入向量库节点：数据持久化
    """

    name = "node_import_milvus"

    def process(self, state: ImportGraphState):
        chunks = state.get("chunks")
        if not chunks:
            logger.error("没有获取到chunks数据，无法进行导入milvus处理")
            raise ValueError("没有获取到chunks数据，无法进行导入milvus处理")
        file_title = chunks[0].get("file_title")

        milvus_client = get_milvus_client()
        collection_name = MilvusConfig.chunks_collection
        if not milvus_client.has_collection(MilvusConfig.chunks_collection):
            schema = milvus_client.create_schema(auto_id=True)
            schema.add_field(
                field_name="id", 
                datatype=DataType.INT64,
                is_primary=True
            ).add_field(
                field_name="title",
                datatype=DataType.VARCHAR,
                max_length=100,
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="content",
                datatype=DataType.VARCHAR,
                max_length=3000
            ).add_field(
                field_name="part",
                datatype=DataType.INT64,
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            )

            # 2. 创建索引index
            index_params = milvus_client.prepare_index_params()
            # 稠密向量的索引
            index_params.add_index(
                field_name="dense_vector",
                index_name="dense_vector_index",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128, "nprobe": 10} # nlist: 聚成128个簇(桶)； nprobe: 查询时搜索最近的10个簇
            )
            index_params.add_index(
                field_name="sparse_vector",
                index_name="sparse_vector_index",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                # params={"inverted_index_algo": "DAAT_MAXSCORE"} # 这个参数可以优化查询
            )
            # 3. 创建表
            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )

        # 导入数据
        # 幂等性删除文件相同的所有chunk
        milvus_client.load_collection(collection_name=MilvusConfig.chunks_collection)
        file_title = file_title.replace("\\", "\\\\").replace("\'", "\\'").replace('\"', '\\"')
        filter = f"file_title == '{file_title}'"
        milvus_client.delete(
            collection_name=MilvusConfig.chunks_collection,
            filter=filter,
        )

        # 去添加chunk到milvus
        res = milvus_client.insert(
            collection_name=MilvusConfig.chunks_collection,
            data=chunks,
        )
        print(res)
        # 回填每个chunk在milvus当中的id到每个chunk，存储到state
        for idx, chunk in enumerate(chunks):
            # chunk["id"] = res.get("ids").pop(0)
            chunk["id"] = res.get("ids")[idx]
                
        return {
            "chunks": chunks
        }

if __name__ == "__main__":
    node = NodeImportMilvus()
    with open(Path(__file__).resolve().parents[3] / "output/chunks_embedding.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)
    init_state = {
        "chunks": chunks,
    }
    result = node(init_state)
    logger.info(json_format(result))