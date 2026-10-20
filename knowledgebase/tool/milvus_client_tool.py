from typing import List

from pymilvus import AnnSearchRequest, MilvusClient, WeightedRanker

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


def get_search_reqs(
    dense_data, 
    dense_anns_field, 
    sparse_data, 
    sparse_anns_field, 
    dense_param=None, 
    sparse_param=None, 
    limit=10,
    expr=None):
  """
  把稠密向量和稀疏向量分别创建自己的检索请求，实例化AnnSearchRequest，拿到实例
  :return: 返回的是两个检索请求的实例组成的列表
  """
  if not dense_param:
    dense_param = {
      "metric_type": "COSINE"
    }
  if not sparse_param:
    sparse_param = {
      "metric_type": "IP"
    } 

  dense_req = AnnSearchRequest(
    data=dense_data,
    anns_field=dense_anns_field,
    param=dense_param,
    limit=limit,
    expr=expr,
  )

  sparse_req = AnnSearchRequest(
    data=sparse_data,
    anns_field=sparse_anns_field,
    param=sparse_param,
    limit=limit,
    expr=expr,
  )
  return [dense_req, sparse_req] # 混合检索需要列表


def hybrid_search(
    collection_name,
    reqs,
    limit=10,
    output_fields=None,
    ranker=(0.5,0.5),
):
  """
  混合检索：稠密向量和稀疏向量的混合检索，需要传递上面那个工具函数返回的请求列表
  """
  milvus_client = get_milvus_client()
  weighted_ranker = WeightedRanker(*ranker) # 解包。加权排名。前面的值对应是稠密，后面的值对应稀疏。
  res = milvus_client.hybrid_search(
    collection_name=collection_name,
    reqs=reqs,
    ranker=weighted_ranker,
    limit=limit,
    output_fields=output_fields
  )
  return res