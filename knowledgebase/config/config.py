import os

from dotenv import load_dotenv
load_dotenv(override=True) # 覆盖系统环境变量当中配置的配置项

class MineruConfig:
  MINERU_API_TOKEN=os.getenv("MINERU_API_TOKEN")

if __name__ == "__main__":
    config = MineruConfig()
    print(config.MINERU_API_TOKEN)
