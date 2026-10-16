import json
import re

from langchain.chat_models import init_chat_model
from pymilvus import DataType

from knowledgebase.config.config import LLMConfig, MilvusConfig
from knowledgebase.config.prompt import ITEM_NAME_SYSTEM_PROMPT, ITEM_NAME_USER_PROMPT_TEMPLATE
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.milvus_client_tool import get_milvus_client


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
        item_name = " ".join(res.content.split())
        item_name = re.sub(r"\s*\((?:Listing\s*)?#?\d{6,}\)", "", item_name, flags=re.IGNORECASE).strip()
        if not item_name:
            item_name = file_title

        milvus_client = get_milvus_client()
        collection_name = MilvusConfig.item_name_collection
        # 判断有没有当前要准备创建的表
        if not milvus_client.has_collection(collection_name):
            # 创建表
            # 1. 创建结构schema
            schema = milvus_client.create_schema(
                auto_id=True,
            )
            schema.add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True,
                is_unique=True,
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=500,
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=500,
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024,
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            )

            # 2. 创建索引index
            index_params = milvus_client.prepare_index_params()
            # 稠密向量的索引
            index_params.add_index(
                field_name="dense_vector", # 给表哪个字段创建索引
                index_name="dense_vector_index",
                index_type="IVF_FLAT",
                metric_type="L2", # 计算相似度的指标算法
                params={"nlist": 128, "nprobe": 10} # nlist是构建索引时，随机选取的向量数据。nlist越大，召回率越高，但构建索引的时间越长
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

        # 5. 把整理的商品名需要向量化，存储到milvus
        # 5-1 幂等性删除.
        # 先删除再插入，删除的时候其实可以是item_name作为过滤条件，file_title作为过滤条件更精准。
        # 大模型识别出来的item_name不是很稳定
        milvus_client.load_collection(MilvusConfig.item_name_collection) # milvus删除数据要先加载某个表才能删除操作

        # 6. 把识别的商品名回填到每个chunk

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