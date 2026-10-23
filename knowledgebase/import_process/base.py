from abc import ABC, abstractmethod
from pathlib import Path
import time

from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger
from knowledgebase.tool.task_utils import add_done_task, add_node_duration, add_running_task

"""
查询流程节点基类
定义统一的节点接口规范，提供通用功能
"""
class NodeBase(ABC):
    name = "node_base"

    def __init__(self):
        if self.name == "node_base":
            logger.error(f"节点类{self.__class__.__name__}必须设置name，代表节点名字")
            raise Exception(f"节点类{self.__class__.__name__}必须设置name，代表节点名字")

    # 这个call的提升就是为了统一干活
    def __call__(self, state: ImportGraphState):
        try:
            logger.info(f"节点{self.name}开始执行")

            # 修改每个节点执行中的状态
            task_id = state.get("task_id")
            add_running_task(task_id, self.name)
            start_time = time.time()

            # 这个call是后期所有的子类对象在当函数使用的时候，都会自动调用这个方法
            result = self.process(state)
            logger.info(f"节点{self.name}执行完成")

            # 修改每个节点执行完成的状态
            add_done_task(task_id, self.name)
            end_time = time.time()

            # 计算每个节点执行所用的时间
            add_node_duration(task_id,self.name,end_time-start_time)
            return result
        except Exception as e:
            logger.error(f"节点{self.name}执行异常: {e}")
            raise e

    @abstractmethod
    def process(self, state: ImportGraphState):
        pass

    def get_output_dir(self, state: ImportGraphState):
        local_dir = state.get("local_dir") or Path(__file__).resolve().parents[2] / "output"
        output_dir = Path(local_dir) / state.get("file_title")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
