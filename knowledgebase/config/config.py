import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
# way1
# load_dotenv(override=True) # 覆盖系统环境变量当中配置的配置项

# way2 使用绝对路径加载.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path=env_path, override=True)

# 如果我们没有指定绝对路径，那么load_dotenv会默认从当前目录开始找.env, 如果没有就往上爬楼，直到找到，找不到就炸
# 我们指定了绝对路径，好处有：
# 1. 效率高，直接去项目根目录找.env 不用往上爬楼
# 2. 安全性高，如果我们在其它目录下也有同名的.env文件，此时不指定绝对路径，在爬楼的时候，第一次碰到.env就直接拿这个.env作为
# 配置文件去使用。此时这个配置文件根本就不是我们项目的配置文件，这样就会造成安全问题


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

class MinIoConfig:

    # MinIO 服务端点
    minio_endpoint=os.getenv('MINIO_ENDPOINT')
    # 访问密钥
    minio_access_key=os.getenv('MINIO_ACCESS_KEY')
    # 私有密钥
    minio_secret_key=os.getenv('MINIO_SECRET_KEY')
    # 存储桶名称
    minio_bucket_name=os.getenv('MINIO_BUCKET_NAME')
    # 图片上传目录
    minio_img_dir=os.getenv('MINIO_IMG_DIR')

class MilvusConfig:

    # Milvus 连接地址
    milvus_url=os.getenv('MILVUS_URL')
    # Milvus 数据库名
    milvus_db_name=os.getenv('MILVUS_DB_NAME')
    # 知识库切片集合名
    chunks_collection=os.getenv('CHUNKS_COLLECTION')
    # 商品名称集合名
    item_name_collection=os.getenv('ITEM_NAME_COLLECTION')

class MongoConfig:
    mongo_url = os.getenv('MONGO_URL')
    mongo_host = os.getenv('MONGO_HOST')
    mongo_port = int(os.getenv('MONGO_PORT'))
    mongo_db_name = os.getenv('MONGO_DB_NAME')

class BGEM3Config:

    # BGE-M3 模型本地路径
    bge_m3_path=os.getenv('BGE_M3_PATH')
    # BGE-M3 模型名称
    bge_m3=os.getenv('BGE_M3')
    # 嵌入模型运行设备（mps / cpu / cuda:0）
    bge_device=os.getenv('BGE_DEVICE')
    # 是否使用半精度
    BGE_FP16=os.getenv('BGE_FP16') in ("True", "true", "1")

class MCPConfig:
    mcp_base_url = os.getenv('MCP_BASE_URL')
    mcp_api_key = os.getenv('MCP_API_KEY')


class RerankConfig:
    rerank_base_url = os.getenv('RERANK_BASE_URL')
    rerank_api_key = os.getenv('RERANK_API_KEY')
    rerank_instruct = os.getenv('TEXT_RERANK_INSTRUCT')

if __name__ == '__main__':
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
    print(os.path.dirname(__file__))

    print('1', os.path.dirname(__file__))
    print('2', os.path.join(os.path.dirname(__file__), "../../.env"))
    print('env_path', env_path)