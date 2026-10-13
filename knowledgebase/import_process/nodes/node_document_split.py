from pathlib import Path
import re

from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger


class NodeDocumentSplit(NodeBase):
    """
    文档切分节点：智能文档切片
    """

    name = "node_document_split"

    def process(self, state: ImportGraphState):
        md_path = state.get("md_path")
        file_title = state.get("file_title")
        if not md_path:
            logger.error("Not provide file path")
            raise Exception("Not provide file path")
        
        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("File does not exist")
            raise Exception("File does not exist")

        if not file_title:
            logger.error("File name does not exist")
            raise Exception("File name does not exist")

        with open(md_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 拿到md的内容，我们要按行切分，所以选择字符串的split方法去按照换行符切分为列表
        md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")
        split_line_list = md_content.split("\n")

        is_block = False # False 代表不在代码围栏里面。True代表在代码围栏里面
        code_pattern = r"^(`{3,}|~{3,})" # 如果后期正则只用一次，那么编译不编译成对象都行
        # code_pattern = re.compile(r"^(`{3,}|~{3,})") # 后期如果一个正则字符串要写多次，我们可以编译成一个正则对象，后期用对象即可
        title_pattern = r'^\s*#{1,6}\s+.+'

        marker = None
        start_index = 0

        temp_section_list = []
        for idx, split_line in enumerate(split_line_list):
            split_line = split_line.strip() # remove space
            # 判断这个行是不是标题
            # ~~~, ```, ```, ~~~
            # 1. 先保证这行不在代码围栏里面
            # 2. 保证这行符合标题的正则
            match = re.match(code_pattern, split_line)
            if match:
                # 拿到了~~~或者```
                if not is_block:
                    # 说明不在代码围栏里面，第一次碰到代码围栏的开始，准备进入
                    is_block = True
                    marker = match.group(1)
                else:
                    if marker == match.group(1):
                        is_block = False
                        marker = None

            if not is_block and re.match(title_pattern, split_line):
                # 一定是标题
                temp_section_list.append(split_line_list[start_index:idx])
                start_index = idx
            
        temp_section_list.append(temp_section_list[start_index:])

        split_section_list = []
        for temp_section in temp_section_list:
            content = "\n".join(temp_section)
            title = temp_section[0] if content.startswith("#") else "No topic"
            split_section_list.append({
                "title": title,
                "content": content,
                "file_title": file_title,
            })

        logger.info(json_format(split_section_list))
        return state

if __name__ == "__main__":
    node = NodeDocumentSplit()
    init_state = {
        "md_path": r"/Users/entingwu/PycharmProjects/EtsyKnowledge/metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom/01_4565343414_cufflinks-gold-groom_new.md",
        "file_title": "01_4565343414_cufflinks-gold-groom_new"
    }
    result = node(init_state)
    logger.info(json_format(result))