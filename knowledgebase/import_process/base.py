from abc import ABC, abstractmethod

from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger

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
            result = self.process(state)
            logger.info(f"节点{self.name}执行完成")
            return result
        except Exception as e:
            logger.error(f"节点{self.name}执行异常: {e}")
            raise e

    @abstractmethod
    def process(self, state: ImportGraphState):
        pass