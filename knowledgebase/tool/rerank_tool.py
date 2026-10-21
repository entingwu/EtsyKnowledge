import dashscope
from http import HTTPStatus

from knowledgebase.config.config import RerankConfig
from knowledgebase.tool.logger import logger
from knowledgebase.tool.json_format import json_format

dashscope.base_http_api_url = RerankConfig.rerank_base_url
dashscope.api_key = RerankConfig.rerank_api_key

def text_rerank(query, texts, limit=10):
  try:
    resp = dashscope.TextReRank.call(
      model="qwen3.7-text-rerank",
      query=query,
      documents=texts,
      top_n=limit, # 这里最终要做断崖检测，获取动态的token。所以这里后期传递的是chunks的列表长度
      instruct=RerankConfig.rerank_instruct,
    )
    if resp.status_code == HTTPStatus.OK:
      # print(resp, type(resp))
      # print(resp.output.results, type(resp.output))
      return [{"index": item.index, "score": item.relevance_score} for item in resp.output.results]
    else:
      logger.error(f"Rerank request failed")
      raise Exception(f"Rerank request failed")
  except Exception as e:
    logger.error(f"Rerank failed, {e}")
    raise e

if __name__ == '__main__':
  chunks = [{
                  "file_title": "001_4565343414_cufflinks-gold-groom",
                  "content": "## Product Highlights\n\n• One pair — 2 cufflinks included\n\n• Choose from our 12-monthBirth Flower Collection\n\n• Each cufflink can feature its own birth flower\n\n• Create a matching pair or combine two meaningful months\n\n• Openwork floral design with a polished gold-plated finish\n\n• Approx. 15 mm / 0.59in face diameter",
                  "part": 1,
                  "item_name": "Birth Flower Cufflinks Gold Groom",
                  "id": 469819117954340289,
                  "title": "## Product Highlights",
                  "score": 0.03225806451612903,
                  "source": "local"
              },
              {
                  "file_title": "001_4565343414_cufflinks-gold-groom",
                  "content": "## Product Overview\n\nPersonalized birth flower cufflinks designed to turn meaningful birth months into a distinctive gold-plated keepsake for the groom, husband, dad, or someone special.\n\nEach cufflink features an openwork floral design representing a meaningful birth month",
                  "part": 1,
                  "item_name": "Birth Flower Cufflinks Gold Groom",
                  "id": 469819117954340287,
                  "title": "## Product Overview",
                  "score": 0.031746031746031744,
                  "source": "local"
              },]
  result = text_rerank(query="How to use Birth Flower Cufflinks?", texts=[chunk.get("content") for chunk in chunks])
  print(json_format(result))
