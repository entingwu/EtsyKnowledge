import json
import asyncio
import re
from urllib.parse import urlparse

from agents.mcp import MCPServerStreamableHttp
from knowledgebase.config.config import MCPConfig
from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger

# 中日韩文字，标题或摘要里出现就认为不是英文网页
CJK_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uff00-\uffef]")

# 批发网站讲的是别家商品和起订量，对客服回复是噪音
# 电商平台和Pinterest上是竞争对手的商品页，出现在回复里等于帮别人引流
EXCLUDE_DOMAINS = [
    "alibaba.com", "aliexpress.com", "made-in-china.com", "dhgate.com", "1688.com",
    "etsy.com", "amazon.com", "ebay.com", "walmart.com", "temu.com", "pinterest.com",
]
# Tavily只排除完全相同的域名，amazon.co.uk、in.pinterest.com这类站点要按主机名再过滤一遍
EXCLUDE_SITE_NAMES = {domain.split(".")[0] for domain in EXCLUDE_DOMAINS}

class NodeWebSearchMcp(NodeBase):
    """
    节点功能，调用外部搜索引擎补充信息
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_web_search_mcp"

    def process(self, state: QueryGraphState):
        rewritten_query = state.get("rewritten_query")
        if not(rewritten_query):
            logger.error("rewritten_query could not be empty")
            raise ValueError("rewritten_query could not be empty")

        # 携程对象，加入时间循环才run。
        res = asyncio.run(self.mcp_run(rewritten_query))
        data = json.loads(res.content[0].text)
        # Tavily失败时（比如429限流）不会抛异常，而是把错误放在返回内容里
        if data.get("error"):
            logger.error(f"Web search failed: status={data.get('status')} detail={data.get('detail')}")
            return {"web_search_docs": []}

        pages = data.get("results") or []
        # Tavily以英文网页为主，再过滤一遍兜底，只保留英文网页，并去掉电商平台的各国站点
        datas = [item for item in pages if self.is_english(item) and self.is_allowed_site(item)]
        logger.info(f"Web search returned {len(pages)} pages, kept {len(datas)} pages")
        logger.info(json_format(datas))

        return {
            "web_search_docs":[
                {
                    "content": item.get("content", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": "web"
                }
                for item in datas
            ]
        }

    def is_english(self, item):
        text = f"{item.get('title', '')} {item.get('content', '')}"
        return not CJK_PATTERN.search(text)

    def is_allowed_site(self, item):
        hostname = urlparse(item.get("url", "")).hostname or ""
        return not EXCLUDE_SITE_NAMES.intersection(hostname.split("."))

    # https://docs.tavily.com/documentation/mcp
    async def mcp_run(self, query, limit=10):
        token = MCPConfig.mcp_api_key
        url = MCPConfig.mcp_base_url
        async with MCPServerStreamableHttp(
            name="Streamable HTTP Python Server",
            params={
                "url": url,
                "headers": {"Authorization": f"Bearer {token}"},
                "timeout": 30,
            },
            cache_tools_list=True,
            max_retry_attempts=3,
        ) as server:
            # 原本用的是智能体的方式，现在我们没办法使用，只能使用调用服务器工具的方法传递工具名的方法去使用，异步操作
            result = await server.call_tool(
                tool_name="tavily_search",
                arguments={
                    "query": query,
                    "max_results": limit,
                    "country": "United States",
                    "exclude_domains": EXCLUDE_DOMAINS,
                }
            )
            return result

if __name__ == "__main__":
    init_state = {
        "rewritten_query": "What kinds of Birth Flower Cufflinks?",
    }
    node_search_embedding = NodeWebSearchMcp()
    result = node_search_embedding(init_state)
    logger.info(json_format(result))