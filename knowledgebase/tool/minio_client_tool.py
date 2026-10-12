# 专门封装单例的minio_client, 一个项目当中拿到一个lclient即可，不需要每次都去创建

import json

from minio import Minio

from knowledgebase.config.config import MinIoConfig


minio_client = None

def get_minio_client():
  global minio_client
  if minio_client is None:
    minio_client = Minio(
      endpoint=MinIoConfig.minio_endpoint,
      access_key=MinIoConfig.minio_access_key,
      secret_key=MinIoConfig.minio_secret_key,
      secure=False, 
      # minio上传文件本质也是在发送http请求，如果这个值是True，它默认是https协议
      # minio用得上http协议，所以这里设置为False. 请求的时候就不会报错使用的是http
    )

    bucket_name = MinIoConfig.minio_bucket_name
    if not minio_client.bucket_exists(bucket_name):
      minio_client.make_bucket(bucket_name)

    # 对桶进行设置权限 写公开 写校验
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetBucketLocation"],
                "Resource": f"arn:aws:s3:::{MinIoConfig.minio_bucket_name}",
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{MinIoConfig.minio_bucket_name}/*",
            },
        ],
    }
    minio_client.set_bucket_policy(bucket_name, json.dumps(policy))

  return minio_client