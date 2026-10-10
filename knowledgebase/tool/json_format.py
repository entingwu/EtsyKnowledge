import json


def json_format(result: str):
  return json.dumps(result, ensure_ascii=False, indent=4)