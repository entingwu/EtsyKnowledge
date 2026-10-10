from pathlib import Path
import os
import re

from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger


class NodeMDImg(NodeBase):
    """
    MarkDown图片处理节点：多模态图片理解
    """

    name = "node_md_img"

    def process(self, state: ImportGraphState):
        md_path = state.get("md_path")
        if not md_path:
            logger.error("md_path could not be empty")
            raise ValueError("md_path could not be empty")

        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("md_path file does not exist")
            raise ValueError("md_path file does not exist")

        with open(md_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 拿到内容，接着需要找到每张图片名字，通过正则从内容当中去拿到图片的位置
        # 获取本地图片的目录，如果不存在，就直接返回原来的内容，因为没有图片需要处理
        image_dir = md_path_obj.parent / "images"
        if not image_dir.exists():
            return {
                "md_content": md_content,
            }
        image_names = os.listdir(image_dir) # 把一个目录当中所有的文件名字组成列表，包括目录名

        if not image_names:
            logger.warning("No image in local image directory")
            return {
                "md_content": md_content,
            }

        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        image_with_context_list = []
        for image_name in image_names:
            suffix = Path(image_name).suffix
            if suffix.lower() not in IMAGE_EXTENSIONS:
                logger.warning(f"图片后缀名不正确")
                continue
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_name) + r"\)")

            match = pattern.search(md_content) # 从内容当中查找正则表达式，找到第一个就结束，如果没有找到，就返回None
            if not match:
                logger.warning("没有找到图片的引用")
                continue
            start, end = match.span() # 拿到每张图片在内容当中的起始位置和结束位置
            print(start, end)
            pre_text = md_content[max(start-300, 0) : start]
            post_text = md_content[end : min(end+300, len(md_content))]
            image_with_context_list.append({
                "image_name": image_name,
                "pre_text": pre_text,
                "post_text": post_text,
                "image_path": str(image_dir / image_name)
            })
        return state

if __name__ == '__main__':
    node = NodeMDImg()
    init_state = {
        "md_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom/01_4565343414_cufflinks-gold-groom.md",
    }
    result = node(init_state)
    print(result)