import os
import shutil
import uuid

from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, UploadFile

app = FastAPI()

# 1. Return json
@app.get('/returnjson')
def returnjson():
  return JSONResponse(
    content={"hello": "world"},
    status_code=200,
    media_type="application/json"
  )

@app.post("/testupload")
def testupload(file: UploadFile):
  print(file.filename)
  print(file.size)
  print(file.content_type)
  print(file.file)
  print(file.headers)

  file_name = str(uuid.uuid4())[:8] + file.filename
  dir_path = "./images"
  if not os.path.exists(dir_path):
    os.makedirs(dir_path)
  fs = open(f"./{dir_path}/{file_name}", "wb")
  shutil.copyfileobj(file.file, fs, length=1024*1024)
  return {"filename": file.filename}

if __name__ == '__main__':
  uvicorn.run(app, host='0.0.0.0', port=8000)