import shutil
import time
import zipfile
from pathlib import Path
import requests

from knowledgebase.config.config import MineruConfig
from knowledgebase.import_process.base import NodeBase
from knowledgebase.import_process.state import ImportGraphState
from knowledgebase.tool.logger import logger

class NodePDFToMD(NodeBase):
    """
    PDF 转 Markdown 节点：PDF结构化解析
    """

    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState):
        local_file_path = state.get("local_file_path")
        local_dir = state.get("local_dir")
        if not local_file_path:
            logger.error(f"Not provide file path: {local_file_path}")
            raise ValueError(f"Not provide file path: {local_file_path}")
        

        local_file_path_obj = Path(local_file_path)
        if not local_file_path_obj.exists():
            logger.error(f"File does not exist: {local_file_path}")
            raise ValueError(f"File does not exist: {local_file_path}")

        # Check output directory
        if not local_dir:
            logger.error(f"local dir could not be empty: {local_dir}")
            raise ValueError(f"local dir could not be empty: {local_dir}")
        
        local_dir_obj = Path(local_dir)
        if not local_dir_obj.exists():
            # parents = True 递归创建
            # exist_ok = True 如果目录已存在，不会抛出异常
            local_dir_obj.mkdir(parents=True, exist_ok=True)

        token = MineruConfig.MINERU_API_TOKEN
        url = "https://mineru.net/api/v4/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                {"name": f"{local_file_path_obj.name}", "data_id": "abcd"}
            ],
            "model_version":"vlm"
        }
        file_path = [local_file_path]

        # Check if request succeeds
        response = requests.post(url,headers=header,json=data)
        if response.status_code != 200:
            logger.error(f"Upload file failed. status:{response.status_code} ,result:{response}")
            raise ValueError(f"Upload file failed. status:{response.status_code} ,result:{response}")

        # Request succeeds, retrieve data from response. Check if data retrieved successfully.
        result = response.json()
        if result["code"] != 0:
            logger.error(f"Upload file fails to retireve data: {result['msg']}")
            raise ValueError(f"Upload file fails to retireve data: {result['msg']}")

        batch_id = result["data"]["batch_id"]
        urls = result["data"]["file_urls"]
        for i in range(0, len(urls)):
            with open(file_path[i], 'rb') as f:
                res_upload = requests.put(urls[i], data=f)
                if res_upload.status_code == 200:
                    logger.info(f"{urls[i]} upload success")
                else:
                    logger.error(f"{urls[i]} upload failed")

        print(f'batch_id: {batch_id}')

        # Used batch id to round robin to retrieve md compressed package from mineru
        url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"

        total_time = 300
        current_time = 0

        # 轮询获取。隔2秒发一次请求，直到拿到需要的结果
        while True:
            try:
                start_time = time.time()
                res = requests.get(url, headers=header)
                # 判断请求成功不成功
                if res.status_code != 200:
                    logger.error(f"获取mineru转化的md的压缩包路径请求失败: {res.status_code} {res.text}")
                    raise ValueError(f"获取mineru转化的md的压缩包路径请求失败: {res.status_code}")

                # 请求成功拿请求体内容
                result = res.json()
                if result["code"] != 0:
                    logger.error(f"获取mineru转化的md的压缩包路径请求数据获取失败: {result.get('msg')}")
                    raise ValueError(f"获取mineru转化的md的压缩包路径请求数据获取失败: {result.get('msg')}")
    
                data = result.get("data")
                # 判断数据拿的对不对
                if data.get("extract_result")[0].get("state") != "done":
                    logger.error("获取mineru转化的md的压缩包路径请求数据获取数据不对，解析还在处理")
                    raise ValueError("获取mineru转化的md的压缩包路径请求数据获取数据不对，解析还在处理")

                url = data.get("extract_result")[0].get("full_zip_url")
                # print(url)
                break
            except Exception as e:
                time.sleep(2)
                end_time = time.time()
                current_time += end_time - start_time
                if current_time > total_time:
                    logger.error("获取mineru转化的md的压缩包路径请求超时")
                    raise ValueError("获取mineru转化的md的压缩包路径请求超时")
                continue

        # Download zip and extract to local_dir/<file stem>
        zip_res = requests.get(url)
        if zip_res.status_code != 200:
            logger.error(f"下载压缩包的内容请求失败: {zip_res.status_code}")
            raise ValueError(f"下载压缩包的内容请求失败: {zip_res.status_code}")

        zip_content = zip_res.content # 获取压缩包的内容
        # 把压缩包的内容写入到本地的zip文件中
        zip_file_path_obj = local_dir_obj / f"{local_file_path_obj.stem}.zip"

        with open(zip_file_path_obj, 'wb') as f:
            f.write(zip_content)


        # 把下载的zip文件解压到本地
        unzip_dir_obj = local_dir_obj / f"{local_file_path_obj.stem}"
        # 幂等性删除
        if unzip_dir_obj.exists():
            shutil.rmtree(unzip_dir_obj)  # 递归删除。 有没有内容都删
        unzip_dir_obj.mkdir(parents=True, exist_ok=True)

        # 打开zip压缩文件，把文件当中的内容解压到指定的目录当中
        with zipfile.ZipFile(zip_file_path_obj) as unzip_content_handler:
            unzip_content_handler.extractall(unzip_dir_obj)
            
        # 把解压出来的文件进行改名处理
        # 第一步找到老文件的位置
        old_md_file_path_obj = unzip_dir_obj / "full.md"
        # 第二步改名处理，但是没有落盘，返回的新的文件路径对象
        new_md_file_path_obj = old_md_file_path_obj.with_name(f"{local_file_path_obj.stem}.md")
        # 第三步真正的改名处理，落盘
        old_md_file_path_obj.rename(new_md_file_path_obj)
        with open(new_md_file_path_obj, 'r', encoding='utf-8') as f:
            md_content = f.read()

        return {
            "md_path":str(new_md_file_path_obj),
            "md_content":md_content
        }

if __name__ == "__main__":
    node = NodePDFToMD()
    init_state = {
        "local_file_path": "metadata/CedarSeaGoods_KB/pdf/01_4565343414_cufflinks-gold-groom.pdf",
        "local_dir": "metadata/CedarSeaGoods_KB/pdf",
    }
    result = node(init_state)
    logger.info(result)