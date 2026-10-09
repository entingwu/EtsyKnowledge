from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState


class NodeEntry(NodeBase):
    """
    入口节点：任务分发
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):

        return state