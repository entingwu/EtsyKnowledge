from pymilvus import MilvusClient

from knowledgebase.config.config import MilvusConfig

# 获取milvus的客户端连接工具
milvus_client = None
def get_milvus_client():
  global milvus_client
  if not milvus_client:
    milvus_client = MilvusClient(
      uri=MilvusConfig.milvus_url,
      db_name=MilvusConfig.milvus_db_name
    )
  return milvus_client