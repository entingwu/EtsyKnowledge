import json
import re
from pathlib import Path

from langchain.chat_models import init_chat_model
from pymilvus import DataType

from knowledgebase.config.config import LLMConfig, MilvusConfig
from knowledgebase.config.prompt import ITEM_NAME_SYSTEM_PROMPT, ITEM_NAME_USER_PROMPT_TEMPLATE
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.milvus_client_tool import get_milvus_client
from knowledgebase.utils.embedding_utils import get_bge_embeddings


class NodeItemNameRecognition(NodeBase):
    """
    主体识别节点：主体识别与标签提取
    """

    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState):
        # 0. 获取数据
        chunks, file_title = self.get_chunks(state)

        # 1. 优先从一级标题中拿到完整的listing标题，拿不到再把部分chunk的内容拼接起来变成一个字符串
        listing_title, listing_id = self.get_listing_title(state.get("md_content") or "")
        context = listing_title or self.get_chunks_str(chunks)

        # 2. 调用大模型把拼接的字符串作为prompt，整理总结主体（商品名）
        item_name = self.get_item_name(file_title, context)

        # 3. 创建milvus连接，并创建表collection
        milvus_client = self.create_milvus_collection()

        # 4、幂等性删除后，把整理的商品名需要向量化存储到milvus,把识别的商品名回填到每个chunk，备份
        # 把整理的商品名需要向量化，存储到milvus
        self.insert_data(milvus_client, item_name, listing_title, listing_id, file_title, chunks, self.get_output_dir(state))

        # 5. 把识别的商品名回填到每个chunk
        return {
            "chunks": chunks,
            "item_name": item_name,
            "listing_title": listing_title,
            "listing_id": listing_id,
        }

    def insert_data(self, milvus_client, item_name, listing_title, listing_id, file_title, chunks, output_dir):
        # 5. 把整理的商品名需要向量化，存储到milvus
        # 5-1 幂等性删除.
        # 先删除再插入，删除的时候其实可以是item_name作为过滤条件，file_title作为过滤条件更精准。
        # 大模型识别出来的item_name不是很稳定
        milvus_client.load_collection(MilvusConfig.item_name_collection) # milvus删除数据要先加载某个表才能删除操作
        # 为了让过滤条件字符串不出现语法错误，我们需要把一些特殊的字符串进行转换
        safe_file_title = file_title.replace("\\", "\\\\").replace("\'", "\\'").replace('\"', '\\"')
        filter = f"file_title == '{safe_file_title}'"
        milvus_client.delete(
            collection_name=MilvusConfig.item_name_collection,
            filter=filter,
        )

        #5-2 把item_name向量化添加到milvus
        embeddings = get_bge_embeddings([listing_title or item_name])
        data = {
            "item_name": item_name,
            "listing_title": listing_title,
            "listing_id": listing_id,
            "file_title": file_title,
            "dense_vector": embeddings.get("dense")[0],
            "sparse_vector": embeddings.get("sparse")[0],
        }
        res = milvus_client.insert(
            collection_name=MilvusConfig.item_name_collection,
            data=data,
        )

        # 回填item_name到每个chunk，并且把chunks备份下个节点去使用
        for chunk in chunks:
            chunk["item_name"] = item_name
            
        # 备份最新的chunks也就是回填完item_name的chunks到本地文件，方便下个节点读取使用
        with open(output_dir / "chunk_item_name.json", "w", encoding="utf-8") as f:
            f.write(json_format(chunks))

    def create_milvus_collection(self):
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
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=500,
            ).add_field(
                field_name="listing_title",
                datatype=DataType.VARCHAR,
                max_length=1000,
            ).add_field(
                field_name="listing_id",
                datatype=DataType.VARCHAR,
                max_length=32,
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
                metric_type="COSINE", # 计算相似度的指标算法
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
        return milvus_client


    def get_item_name(self, file_title, chunks_str):
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
            return item_name
    
    def get_listing_title(self, md_content):
        match = re.search(r"^#\s+(.+?)\s*\((?:Listing\s*)?#?(\d{6,})\)\s*$", md_content, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(), match.group(2)
        return "", ""

    def get_chunks_str(self, chunks):
        chunk_k_list = chunks[:15]
        chunks_str = ""
        max_length = 10000
        for idx, chunk in enumerate(chunk_k_list, start=1):
            title = chunk.get("title")
            content = chunk.get("content")
            chunk_text = f"[chunk{idx}\ntitle: {title}\ncontent: {content}]\n\n"
            chunks_str += chunk_text
            if len(chunks_str) > max_length:
                break
        chunks_str = chunks_str[:max_length]
        return chunks_str
    
    def get_chunks(self, state: ImportGraphState):
        chunks = state.get("chunks")
        file_title = state.get("file_title")
        if not chunks or not file_title:
            logger.error("chunks and title could not be empty.")
            raise ValueError("chunks and title could not be empty.")
        return chunks, file_title

    

if __name__ == '__main__':
    node = NodeItemNameRecognition()
    with open(Path(__file__).resolve().parents[3] / "output/001_4565343414_cufflinks-gold-groom/chunks.json", "r", encoding="utf-8") as f:
        # chunks = f.read()
        chunks = json.load(f)
    init_state = {
        # "chunks": json.loads(chunks)
        "chunks": chunks,
        "file_title": "001_4565343414_cufflinks-gold-groom"
    }
    result = node(init_state)
    # logger.info(json_format(result))