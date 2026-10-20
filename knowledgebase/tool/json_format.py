import json

import numpy as np
from bson import ObjectId

class NumpyEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    return super().default(obj)


def json_format(result: str):
  return json.dumps(result, ensure_ascii=False, indent=4, cls=NumpyEncoder)
