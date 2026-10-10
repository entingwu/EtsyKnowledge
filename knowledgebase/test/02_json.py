import json
from pathlib import Path


data = {
  "name": "christy",
  "age": 28,
  "gender": "female",
  "height": 165
}

print(data, type(data))

# 先把字典序列化, 然后返回给前端
data_json = json.dumps(data)
print(data_json, type(data_json))

# 把json串反序列化为字典
json_data = json.loads(data_json) # 把json串反序列化为字典
print(json_data, type(json_data))
json_data["name"] = "steve"

# 把数据进行转化后，和文件进行操作
data2 = {
  "name": "charles",
  "age": 6,
}

json_path = Path(__file__).parent / "data.json"

with open(json_path, "w", encoding="utf-8") as f:
  json.dump(data2, f, ensure_ascii=False, indent=2)

with open(json_path, "r", encoding="utf-8") as f:
  python_dict = json.load(f)
  print(python_dict, type(python_dict))