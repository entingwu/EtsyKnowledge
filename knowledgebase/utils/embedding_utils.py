from typing import List

from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from knowledgebase.config.config import BGEM3Config
from knowledgebase.tool.json_format import json_format
# 后期数据是跟milvus打交道，采用milvus封装的类去初始化兼容性会更好

bgem3_model = None
def get_bgem3_model():
    global bgem3_model;
    if not bgem3_model:
        bgem3_model = BGEM3EmbeddingFunction(
            model_name=BGEM3Config.bge_m3_path,
            device=BGEM3Config.bge_device,
            use_fp16=BGEM3Config.BGE_FP16
        )
    return bgem3_model

def get_bge_embeddings(texts: List[str]):
    model = get_bgem3_model()
    embeddings = model.encode_documents(texts)
    # 获取稠密向量，是一个list
    # print('@', embeddings.get("dense"), type(embeddings.get("dense")))
    # 获取列表当中第一个稠密向量，是numpy.ndarray
    # print('@', embeddings.get("dense")[0], type(embeddings.get("dense")[0]))
    # 获取列表当中第一个稠密向量第一个元素，是numpy.float16
    # print('@', embeddings.get("dense")[0][0], type(embeddings.get("dense")[0][0]))

    # 把稀疏向量打印打印的对象，尝试转化字典去打印，就可以看到内部的详细内容
    # print('@', embeddings.get("sparse").__dict__, type(embeddings.get("sparse")))
    # for sparse_item in embeddings.get("sparse"):
    #     print('$', dict(zip(sparse_item.indices.tolist(), sparse_item.data.tolist())))

    return {
        "dense": [item.tolist() for item in embeddings.get("dense")],
        "sparse": [
            dict(zip(sparse_item.indices.tolist(), sparse_item.data.tolist())) # key-value
            for sparse_item in embeddings.get("sparse")
        ]
    }


if __name__ == '__main__':
    text_list = ["I love Charles", "I love Henry"]
    result = get_bge_embeddings(text_list)
    print(json_format(result))
    for idx, text in enumerate(text_list):
        dense = result["dense"][idx]
        sparse = result["sparse"][idx]
        print(f"{text}: dense 维度 {len(dense)}, 前5个值 {dense[:5]}")
        print(f"{text}: sparse 非零个数 {len(sparse)}, {sparse}")