import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
load_dotenv(override=True) # 覆盖系统环境变量当中配置的配置项

# https://bailian.console.aliyun.com/cn-beijing/model/market/detail/qwen3-vl-flash?serviceSite=asia-pacific-china&ref=search_result&kw=qwen3-vl-flash

class MineruConfig:
  MINERU_API_TOKEN=os.getenv("MINERU_API_TOKEN")

if __name__ == "__main__":
    config = MineruConfig()
    print(config.MINERU_API_TOKEN)

class LLMConfig:
  openai_api_key=os.getenv('OPENAI_API_KEY')
  # API 基础地址（阿里云 DashScope）
  openai_api_base=os.getenv('OPENAI_API_BASE')
  # 默认 LLM 模型
  llm_default_model=os.getenv('LLM_DEFAULT_MODEL')
  # 默认温度参数（0-1，越低越稳定）
  llm_default_temperature=float(os.getenv('LLM_DEFAULT_TEMPERATURE'))
  # 视觉语言模型
  vl_model=os.getenv('VL_MODEL')
  # 商品名识别模型
  item_model=os.getenv('ITEM_MODEL')
