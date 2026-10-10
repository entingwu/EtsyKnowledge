import json

from knowledgebase.import_process.base import NodeBase
from knowledgebase.tool.json_format import json_format
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
        "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
    }
    result = node(init_state)
    logger.info(json_format(result))