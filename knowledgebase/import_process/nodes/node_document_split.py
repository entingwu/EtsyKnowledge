import json
from pathlib import Path
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        # Step 1. 获取内容和文件名
        md_content, file_title = self.get_md_content(state)

        # Step 2. 对内容进行初切，以标题为标记进行合并片段
        split_section_list = self.get_split_section_list(md_content, file_title)

        # Step 3. 对片段内容比较长的进行长切得到最终的chunks
        final_chunk_list = self.get_final_chunk_list(split_section_list, file_title)
        
        with open(r"/Users/entingwu/PycharmProjects/EtsyKnowledge/data/chunks.json", "w", encoding="utf-8") as f:
            f.write(json_format(final_chunk_list))
            # json.dump(final_chunk_list, f, ensure_ascii=False, indent=4)
        return {
            "chunks": final_chunk_list
        }

    def get_split_section_list(self, md_content, file_title):
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
            
        temp_section_list.append(split_line_list[start_index:])
        # 把切分出来的每个小列表对应整理成字典，就是我们粗切出来的每个section
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
        return split_section_list

    def get_final_chunk_list(self, split_section_list, file_title):
        # 细切，长切短合
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "。", "！", "？", "；", "!", "?", ";", ".", " "],
            chunk_size = 300,
            chunk_overlap = 50,
        )

        final_chunk_list = []
        for split_section in split_section_list:
            # 获取每个区块的内容，根据内容判断长度是不是超过指定的长度，如果超过就再去切分，如果不超过就不切
            title = split_section.get("title")
            content = split_section.get("content")
            real_content = content[len(title) + 2:] if content.startswith("#") else content 

            # 有多少个keyvalue，milvus就有多少个字段
            if len(real_content) < 300:
                final_chunk_list.append({
                    **split_section,
                    "part": 0, # 这个数据目的是为了溯源，没有被切的编号为0
                })
                continue

            if "<table" in real_content:
                final_chunk_list.append({
                    **split_section,
                    "part": 0, 
                })
                continue

            for idx, split_text in enumerate(splitter.split_text(real_content), start=1):
                # 把切成每个小块文本，也得组装成一个chunk字典，存入final_chunk_list
                final_chunk_list.append({
                    "title": title,
                    "content": title + "\n\n" + split_text,
                    "file_title": file_title,
                    "part": idx, 
                })
        
        logger.info(json_format(final_chunk_list))
        return final_chunk_list

    def get_md_content(self, state: ImportGraphState):
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
        return md_content, file_title


if __name__ == "__main__":
    node = NodeDocumentSplit()
    init_state = {
        "md_path": r"/Users/entingwu/PycharmProjects/EtsyKnowledge/metadata/CedarSeaGoods_KB/listings/02_wedding-keepsakes/001_4565343414_cufflinks-gold-groom.md",
        "file_title": "001_4565343414_cufflinks-gold-groom"
    }
    result = node(init_state)
    logger.info(json_format(result))