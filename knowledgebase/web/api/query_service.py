import json
import uuid

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Body, Path
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from knowledgebase.query_process.main_graph import QueryMainGraphRunner
from knowledgebase.tool.logger import logger
from knowledgebase.tool.mongo_tool import clear_history, get_recent_messages
from knowledgebase.tool.task_utils import create_queue, put_data, get_data, get_task_info, update_task_status, TASK_STATUS_PROCESSING, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED

app = FastAPI(
    title="EtsyKnowledge Query Service",
    description="检索模块各个api接口服务",
    version="0.0.1"
)

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)


class QueryParams(BaseModel):
  query: str = Field(..., description="查询问题")
  session_id: str = Field(..., description="会话id")


# 后台任务，调用graph
def run_main_graph(task_id: str, original_query: str, session_id: str):
  try:
    init_state = {
      "task_id": task_id,
      "session_id": session_id,
      "original_query": original_query,
    }

    # 这个模块我们要用的是sso后端主动推送，我们需要把修改的数据存队列，还得写sse接口生成器流式推送。
    # 更新总状态，放到队列，sse后期就可以从队列当中取出更新的数据状态推送给前端
    update_task_status(task_id, TASK_STATUS_PROCESSING)
    put_data(task_id, "progress", get_task_info(task_id))

    QueryMainGraphRunner.create_and_run(init_state)
    # 检索完成后，更新状态为已完成
    update_task_status(task_id, TASK_STATUS_COMPLETED)
    put_data(task_id, "progress", get_task_info(task_id))

  except Exception as e:
    # 检索失败
    logger.error(f"执行查询graph异常，task_id={task_id}: {e}")
    update_task_status(task_id, TASK_STATUS_FAILED)
    put_data(task_id, "error", {"error": str(e), **get_task_info(task_id)})


@app.post("/query")
async def query(background_tasks: BackgroundTasks, query_params: QueryParams = Body(..., description="查询参数")):
  task_id = str(uuid.uuid4())
  # 先创建队列，后台任务和sse接口都从这个队列存取数据
  create_queue(task_id)

  # 添加后台任务执行
  background_tasks.add_task(run_main_graph, task_id, query_params.query, query_params.session_id)
  return {
    "message": "结果正在处理中...",
    "task_id": task_id,
    "session_id": query_params.session_id,
  }


def generate_stream(task_id: str):
  while True:
    item = get_data(task_id)
    yield f"event: {item.get('event')}\n"
    yield f"data: {json.dumps(item.get('data'), ensure_ascii=False)}\n\n"
    # final或者error之后前端会关闭连接，这里也结束循环，避免线程一直阻塞在队列上
    if item.get("event") in ("final", "error"):
      break


@app.get("/stream/{task_id}")
def stream(task_id: str = Path(..., description="任务ID")):
  return StreamingResponse(
    generate_stream(task_id),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no"
    }
  )


@app.get("/history/{session_id}")
async def get_history(session_id: str = Path(..., description="会话id"), limit: int = 50):
  # 查出来是按时间倒序，前端展示要按时间正序
  history_list = reversed(get_recent_messages(session_id, n=limit))
  # 在对数据做序列化的时候，ObjectId类型会报错
  items = [
    {
      **item,
      "_id": str(item.get("_id")),
      # "session_id": item.get("session_id", ""),
      # "role": item.get("role", ""),
      # "text": item.get("text", ""),
      # "rewritten_query": item.get("rewritten_query", ""),
      # "item_names": item.get("item_names") or [],
      # "image_urls": item.get("image_urls") or [],
      # "ts": item.get("ts"),
    }
    for item in history_list
  ]
  return {"session_id": session_id, "items": items}


@app.delete("/history/{session_id}")
async def delete_history(session_id: str = Path(..., description="会话id")):
  clear_history(session_id)
  return {"message": "History cleared"}


@app.get("/health")
async def health(): 
  return {"ok": True}


if __name__ == '__main__':
  uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001, # 另一个服务
  )
