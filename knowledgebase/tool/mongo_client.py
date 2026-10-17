# 这个文件是专门给mongodb的操作做了封装，后期操作mongo的增删改查全部都对应这个文件当中一个函数
# 1. 获取单例的mongo链接对象
from pymongo import MongoClient
from pymongo import ASCENDING, DESCENDING

from knowledgebase.config.config import MongoConfig

mongo_client = None
def get_mongo_client():
  global mongo_client
  if not mongo_client:
    mongo_client = MongoClient(MongoConfig.mongo_url)
    print(mongo_client)
  return mongo_client

mongo_tool = None
def get_mongo_tool():
  global mongo_tool
  if not mongo_tool:
    mongo_client = get_mongo_client() # 获取连接对象，目的是为了创建数据库
    db = mongo_client[MongoConfig.mongo_db_name] # 创建数据获取数据库对象
    mongo_tool = db["chat_message"] # 创建集合对象，获取集合对象
    mongo_tool.create_index([("session_id", ASCENDING), ("ts", DESCENDING)]) # 创建索引
  return mongo_tool

# 表的增删改查
# clear_history清空某个session_id的所有消息
def clear_history(session_id):
  mongo_tool = get_mongo_tool()
  mongo_tool.delete_many({"session_id": session_id})

#	get_recent_messages 根据session_id获取最近的n条消息
def get_recent_messages(session_id, n=10):
  mongo_tool = get_mongo_tool()
  result = mongo_tool.find({"session_id": session_id}).sort({"ts": -1}).limit(n)
  return result

# 增改一体
#	save_chat_message保存历史记录（根据id决定是添加还是修改）
# 一条数据如果是新增，那么它还没进入到数据库，此时不可能有id
# 一条数据如果是修改，那么代表这条数据是从数据库里面取出来，一定有id
def save_chat_message():
  pass

#	update_message_item_names 把通过意图判断获取的item_names添加到对应的历史消息当中

#	MongoJSONEncoder类，配置打印结果的json系列化工具，否则ObjectId类型在序列化的时候报错

if __name__ == "__main__":
  client = get_mongo_client()
  print(client.admin.command("ping"))
  tool = get_mongo_tool()