# 下载模型到当前目录下的 models/bge-m3 文件夹
# model_dir = snapshot_download('Xorbits/bge-m3', cache_dir='D:/ai_models/modelscope_cache/models')
# print(f"模型已下载到: {model_dir}")

from pathlib import Path

from modelscope.hub.snapshot_download import snapshot_download

local_dir = Path('/Users/entingwu/Documents/Models/bge-m3')

# 已有模型就不下载，避免覆盖共用的模型文件
if (local_dir / 'pytorch_model.bin').exists():
    print(f"模型已存在，跳过下载: {local_dir}")
else:
    # 下载模型到当前目录下的 models/bge-m3 文件夹
    model_dir = snapshot_download('BAAI/bge-m3', local_dir=str(local_dir))
    print(f"模型已下载到: {model_dir}")