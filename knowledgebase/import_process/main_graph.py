from langgraph.graph import END, START, StateGraph

from knowledgebase.import_process.state import ImportGraphState

from knowledgebase.import_process.nodes.node_bge_embedding import NodeBGEEmbedding
from knowledgebase.import_process.nodes.node_document_split import NodeDocumentSplit
from knowledgebase.import_process.nodes.node_entry import NodeEntry
from knowledgebase.import_process.nodes.node_import_milvus import NodeImportMilvus
from knowledgebase.import_process.nodes.node_item_name_recognition import NodeItemNameRecognition
from knowledgebase.import_process.nodes.node_md_img import NodeMDImg
from knowledgebase.import_process.nodes.node_pdf_to_md import NodePDFToMD
from knowledgebase.tool.logger import logger


# Step 3
# builder = StateGraph(state_schema=ImportGraphState)

# Step 4
# builder.add_node(NodeEntry.name, NodeEntry())
# builder.add_node(NodePDFToMD.name, NodePDFToMD())
# builder.add_node(NodeMDImg.name, NodeMDImg())
# builder.add_node(NodeDocumentSplit.name, NodeDocumentSplit())
# builder.add_node(NodeItemNameRecognition.name, NodeItemNameRecognition())
# builder.add_node(NodeBGEEmbedding.name, NodeBGEEmbedding())
# builder.add_node(NodeImportMilvus.name, NodeImportMilvus())

# builder.add_edge(START, NodeEntry.name)
# # builder.set_entry_point(NodeEntry.name) # Equivalent

# builder.add_conditional_edges(NodeEntry.name, after_entry_router, path_map={
#   "pdf_to_md": NodePDFToMD.name,
#   "md_img": NodeMDImg.name,
#   "end": END
# })

# builder.add_edge(NodePDFToMD.name, NodeMDImg.name)
# builder.add_edge(NodeMDImg.name, NodeItemNameRecognition.name)
# builder.add_edge(NodeDocumentSplit.name, NodeItemNameRecognition.name)
# builder.add_edge(NodeItemNameRecognition.name, NodeBGEEmbedding.name)
# builder.add_edge(NodeBGEEmbedding.name, NodeImportMilvus.name)
# builder.add_edge(NodeImportMilvus.name, END)

# Step 6
# graph = builder.compile()

# Step 7
# init_state = {
#     "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
# }
# result = graph.invoke(init_state)
# logger.info(result)


class MainGraphRunner:

  def __init__(self):
    self.builder = StateGraph(state_schema=ImportGraphState)
    self.add_nodes()
    self.add_edges()
    self.graph = None

  def add_nodes(self):
    self.builder.add_node(NodeEntry.name, NodeEntry())
    self.builder.add_node(NodePDFToMD.name, NodePDFToMD())
    self.builder.add_node(NodeMDImg.name, NodeMDImg())
    self.builder.add_node(NodeDocumentSplit.name, NodeDocumentSplit())
    self.builder.add_node(NodeItemNameRecognition.name, NodeItemNameRecognition())
    self.builder.add_node(NodeBGEEmbedding.name, NodeBGEEmbedding())
    self.builder.add_node(NodeImportMilvus.name, NodeImportMilvus())

  def add_edges(self):
    self.builder.add_edge(START, NodeEntry.name)
    self.builder.add_conditional_edges(NodeEntry.name, self.after_entry_router, path_map={
      "pdf_to_md": NodePDFToMD.name,
      "md_img": NodeMDImg.name,
      "end": END
    })

    self.builder.add_edge(NodePDFToMD.name, NodeMDImg.name)
    self.builder.add_edge(NodeMDImg.name, NodeItemNameRecognition.name)
    self.builder.add_edge(NodeDocumentSplit.name, NodeItemNameRecognition.name)
    self.builder.add_edge(NodeItemNameRecognition.name, NodeBGEEmbedding.name)
    self.builder.add_edge(NodeBGEEmbedding.name, NodeImportMilvus.name)
    self.builder.add_edge(NodeImportMilvus.name, END)


  # 条件边的路由函数
  def after_entry_router(self, state):
    is_pdf_read_enabled = state.get("is_pdf_read_enabled")
    is_md_read_enabled = state.get("is_md_read_enabled")

    if is_pdf_read_enabled:
      return "pdf_to_md"
    elif is_md_read_enabled:
      return "md_img"
    else:
      return "end"

  def run(self, state):
    """
    作用: 1. 懒加载， 2.如果一个人同时执行graph多次, 不能重复编译。
    """
    if self.graph is None:
      self.graph = self.builder.compile()

    result = self.graph.invoke(state)
    return result

  @classmethod
  def create_and_run(cls, state):
    return cls().run(state)

if __name__ == '__main__':
  # runner = MainGraphRunner()
  # init_state = {
  #     "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
  # }
  # result = runner.run(init_state)
  # logger.info(result)

  init_state = {
      "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
  }
  result = MainGraphRunner.create_and_run(init_state)
  logger.info(result)