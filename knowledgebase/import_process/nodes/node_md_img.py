import base64
from collections import deque
from pathlib import Path
import os
import re
import time

from langchain.chat_models import init_chat_model
from minio.error import S3Error

from knowledgebase.config.config import LLMConfig, MinIoConfig
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.minio_client_tool import get_minio_client
from knowledgebase.tool.logger import logger

class NodeMDImg(NodeBase):
    """
    MarkDown图片处理节点：多模态图片理解
    """

    name = "node_md_img"

    def process(self, state: ImportGraphState):
        md_content, md_path_obj = self.get_md_content(state)

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

        image_with_context_list = self.get_image_with_context_list(md_content, image_dir, image_names)

        image_with_summary_list = self.get_image_with_summary_list(image_with_context_list, md_path_obj.stem)

        image_with_summary_url_list = self.get_image_with_summary_url_list(
            image_with_summary_list, md_path_obj
        )

        md_content, new_md_path_obj = self.replace_md_content(
            md_content, image_with_summary_url_list, md_path_obj
        )

        return {
            "md_path": str(new_md_path_obj),
            "md_content": md_content,
        }


    def replace_md_content(self, md_content, image_with_summary_url_list, md_path_obj):
        # 把md_content当中的图片路径替换成在线的图片url，摘要也要做替换
        for image_with_summary_url in image_with_summary_url_list:
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_with_summary_url.get("image_name")) + r"\)")
            # 使用自己给定的字符串替换md_content当中符合正则的子串
            # md_content = pattern.sub(
            #     f"![{image_with_summary_url.get('summary')}]({image_with_summary_url.get('url')})",
            #     md_content
            # )

            # 替换的时候字符串采用lambda表达式返回的方式去做。好处是这样的写法如果碰到字符串中有特殊字符不会炸。
            md_content = pattern.sub(
                lambda m : f"![{image_with_summary_url.get('summary')}]({image_with_summary_url.get('url')})",
                md_content
            )
        # 构造最新的md文件路径，把替换完成的内容写到最新的文件
        new_md_path_obj = md_path_obj.parent / f"{md_path_obj.stem}_new.md"
        with open(new_md_path_obj, 'w', encoding="utf-8") as f:
            f.write(md_content)
        return md_content, new_md_path_obj

    def get_image_with_summary_url_list(self, image_with_summary_list, md_path_obj):
        # 后面接着上面的继续搞url
        # 上传图片获取图片的在线url
        minio_client = get_minio_client()
        
        # 图片文件名是内容哈希，所有listing共用一个目录：同一张照片只存一份、只有一个url
        # 所以不再按listing分目录，也不做幂等性删除（共用的图片可能还被别的listing引用）
        upload_dir = MinIoConfig.minio_img_dir
        bucket_name = MinIoConfig.minio_bucket_name

        image_with_summary_url_list = []
        for image_with_summary in image_with_summary_list:
            object_name = f"{upload_dir}/{image_with_summary.get('image_name')}" # 目录名 + 文件名
            if self.object_exists(minio_client, bucket_name, object_name):
                logger.info(f"图片已存在，跳过上传: {object_name}")
            else:
                minio_client.fput_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=image_with_summary.get("image_path")
                )

            url = f"http://{MinIoConfig.minio_endpoint}/{bucket_name}/{object_name}"
            image_with_summary_url_list.append({
                **image_with_summary,
                "url": url,
            })

        logger.info(json_format(image_with_summary_url_list))
        return image_with_summary_url_list

    def object_exists(self, minio_client, bucket_name, object_name):
        try:
            minio_client.stat_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    def get_md_content(self, state: ImportGraphState):
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
        return md_content, md_path_obj

    def get_image_with_context_list(self, md_content, image_dir, image_names):
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
                logger.warning(f"没有找到图片的引用: {image_name}")
                continue

            start, end = match.span() # 拿到每张图片在内容当中的起始位置和结束位置
            pre_text = md_content[max(start-300, 0) : start]
            post_text = md_content[end : min(end+300, len(md_content))]
            image_with_context_list.append({
                "image_name": image_name,
                "pre_text": pre_text,
                "post_text": post_text,
                "image_path": str(image_dir / image_name)
            })
        return image_with_context_list

    def get_image_with_summary_list(self, image_with_context_list, file_title):
        # 我们就可以把图片的上下文 图片的内容 我们自己写的提示词 交给大模型去帮我们整理摘要（视觉大模型）
        llm = init_chat_model(
            model=LLMConfig.vl_model,
            model_provider="openai",
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature
        )

        dq = deque(maxlen=30) # 双端队列
        # 把摘要总结完成暂存到列表
        image_with_summary_list = []

        for image_with_context in image_with_context_list:
            current_time = time.time()
            # 拿到每张图片的字典，按道理来说就得调用大模型，但是大模型有频率限制，得先做大模型的限频操作
            # 令牌桶 滑动门实现限频操作。
            # 1. 设计一个队列，这个队列的长度就是你要限定的频率的上限。一般是模型频率上限 * 80%
            # 2. 这个队列当中保存的是每个图片调用大模型发请求的时间
            # 3. 队列当中每个请求的时间最多能待一分钟
            # 4. 队列当中最多能放2400个时间，如果第2401个请求来了，第一个时间还没有超过1分钟，就得等待
            # 5. 只有队列当中有位置了，才能继续发请求。

            # 第一步：盲清一波
            while dq and current_time - dq[0] > 60:
                dq.popleft() # 清除队列的第一个人

            # 第二步：队列只有两种状态。要么满了，要么有空位
            if len(dq) == dq.maxlen:
                # 满了就得等待，计算等待的时间
                need_wait_time = 60 - (current_time - dq[0])
                if need_wait_time > 0:
                    time.sleep(need_wait_time)

                current_time = time.time()
                while dq and current_time - dq[0] > 60:
                    dq.popleft() # 清除队列的第一个人

            dq.append(current_time) # 令牌分发
            # 整理图片的内容交给大模型有两种方式，一种是把图片的二进制数据发给大模型，一种是把图片的URL发给大模型
            
            with open(image_with_context.get("image_path"), "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{self.get_image_mime_type(image_with_context.get('image_path'))};base64,{base64_data}"
                            },
                        },
                        {"type": "text", "text": f"""This is an image. The text before the image is: "{image_with_context.get('pre_text')}"
                            The text after the image is: "{image_with_context.get('post_text')}"
                            Briefly summarize this image in English, in no more than 50 words."""
                        },
                    ],
                },
            ]

            try:
                res = llm.invoke(input=messages)
                summary = self.clean_summary(res.content)
            except Exception as e:
                # 单张图片摘要失败（例如内容审核误判）不影响整个文件，用通用描述兜底
                logger.warning(f"图片{image_with_context.get('image_name')}摘要生成失败，使用通用描述: {e}")
                summary = self.get_fallback_summary(file_title)

            image_with_summary_list.append({
                "image_name": image_with_context.get("image_name"),
                "summary": summary,
                "image_path": image_with_context.get("image_path"),
            })
        return image_with_summary_list

    def get_fallback_summary(self, file_title):
        product = re.sub(r"^\d+_\d+_", "", file_title).replace("-", " ").replace("_", " ").strip()
        return f"Product image of {product}" if product else "Product image"

    def get_image_mime_type(self, image_path):
        suffix = Path(image_path).suffix.lower()
        return "image/jpeg" if suffix in {".jpg", ".jpeg"} else f"image/{suffix.lstrip('.')}"

    def clean_summary(self, summary):
        return " ".join(summary.replace("[", "(").replace("]", ")").split())

if __name__ == '__main__':
    node = NodeMDImg()
    init_state = {
        "md_path": str(Path(__file__).resolve().parents[3] / "metadata/CedarSeaGoods_KB/listings/02_wedding-keepsakes/001_4565343414_cufflinks-gold-groom.md"),
    }
    result = node(init_state)
    print(result)
