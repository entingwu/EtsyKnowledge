from knowledgebase.import_process.base import NodeBase
from knowledgebase.tool.logger import logger


class TestNode(NodeBase):
    name = "test_node"
    def process(self, state):
        # 在这里实现节点的处理逻辑
        print(f"Processing state: {state}")
        return state

if __name__ == '__main__':
    node = TestNode()
    init_state = {
        "name": "test_node",
    }
    result = node(init_state)
    logger.info(result)