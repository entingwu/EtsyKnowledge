from pathlib import Path

from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool import logger


class NodeEntry(NodeBase):
    """
    入口节点：任务分发
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):
        local_file_path = state.get("local_file_path")
        if not local_file_path:
            logger.error(f"Not provide file path: {local_file_path}")
            raise Exception(f"Not provide file path: {local_file_path}")

        local_file_path_obj = Path(local_file_path)
        if not local_file_path_obj.exists():
            logger.error(f"File does not exist: {local_file_path}")
            raise Exception(f"File does not exist: {local_file_path}")

        suffix = local_file_path_obj.suffix.lower()
        file_title = local_file_path_obj.stem # no suffix
        if suffix.lower() == ".pdf":
            return {
                "is_pdf_read_enabled": True,
                "file_title": file_title,
                "pdf_path": str(local_file_path_obj)
            }
        elif suffix.lower() == ".md":
            return {
                "is_md_read_enabled": True,
                "file_title": file_title,
                "md_path": str(local_file_path_obj)
            }
        else:
            logger.error(f"Unsupported file type: {suffix}")
            raise Exception(f"File {local_file_path_obj} does not support. Only support pdf and md file type.")

if __name__ == '__main__':
    node = NodeEntry()
    init_state = {
        "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
    }
    result = node(init_state)
    print(result)