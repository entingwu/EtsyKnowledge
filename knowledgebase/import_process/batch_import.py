import argparse
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import colorlog

from knowledgebase.config.config import MilvusConfig
from knowledgebase.import_process.main_graph import MainGraphRunner
from knowledgebase.tool.logger import logger
from knowledgebase.tool.milvus_client_tool import get_milvus_client
from knowledgebase.tool.minio_client_tool import get_minio_client
from knowledgebase.utils.embedding_utils import get_bgem3_model

ROOT_DIR = Path(__file__).resolve().parents[2]


def main():
    args = parse_args()
    set_log_format()

    pdf_paths = sorted(Path(args.pdf_dir).rglob("*.pdf"))
    if args.only:
        pdf_paths = [p for p in pdf_paths if args.only in str(p)]
    if args.limit:
        pdf_paths = pdf_paths[:args.limit]

    # 共享的客户端和模型都是懒加载的单例，并发前先在主线程初始化，避免多个线程同时初始化
    get_milvus_client()
    get_minio_client()
    get_bgem3_model()

    imported_titles = set() if args.force else get_imported_titles()
    todo_paths = [p for p in pdf_paths if p.stem not in imported_titles]
    logger.info(f"共{len(pdf_paths)}个PDF，已导入跳过{len(pdf_paths) - len(todo_paths)}个，待导入{len(todo_paths)}个，并发{args.workers}")

    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(import_one, path, args.local_dir) for path in todo_paths]
        for idx, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            logger.info(f"进度{idx}/{len(todo_paths)} {result['status']} {result['file_title']} {result['seconds']}s")

    write_report(results, pdf_paths, todo_paths, round(time.time() - start), args.local_dir)


def import_one(pdf_path, local_dir):
    threading.current_thread().name = pdf_path.stem[:3]
    start = time.time()
    try:
        result = MainGraphRunner.create_and_run({
            "local_file_path": str(pdf_path),
            "local_dir": local_dir,
        })
        return {
            "status": "OK",
            "file_title": pdf_path.stem,
            "seconds": round(time.time() - start),
            "chunks": len(result.get("chunks", [])),
            "item_name": result.get("item_name"),
            "listing_id": result.get("listing_id"),
        }
    except Exception as e:
        logger.error(f"{pdf_path.stem}导入失败: {e}\n{traceback.format_exc()}")
        return {
            "status": "FAIL",
            "file_title": pdf_path.stem,
            "seconds": round(time.time() - start),
            "pdf_path": str(pdf_path),
            "error": repr(e),
        }


def get_imported_titles():
    milvus_client = get_milvus_client()
    if not milvus_client.has_collection(MilvusConfig.chunks_collection):
        return set()
    milvus_client.load_collection(MilvusConfig.chunks_collection)
    imported_titles = set()
    iterator = milvus_client.query_iterator(
        collection_name=MilvusConfig.chunks_collection,
        filter="",
        output_fields=["file_title"],
        batch_size=1000,
    )
    while True:
        rows = iterator.next()
        if not rows:
            iterator.close()
            break
        imported_titles.update(row["file_title"] for row in rows)
    return imported_titles


def write_report(results, pdf_paths, todo_paths, total_seconds, local_dir):
    ok_results = [r for r in results if r["status"] == "OK"]
    fail_results = [r for r in results if r["status"] == "FAIL"]
    report = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "total_pdfs": len(pdf_paths),
        "skipped": len(pdf_paths) - len(todo_paths),
        "ok": len(ok_results),
        "fail": len(fail_results),
        "total_seconds": total_seconds,
        "total_chunks": sum(r["chunks"] for r in ok_results),
        "failures": fail_results,
        "results": sorted(ok_results, key=lambda r: r["file_title"]),
    }
    report_path = Path(local_dir) / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"批量导入完成: 成功{len(ok_results)}，失败{len(fail_results)}，跳过{report['skipped']}，用时{total_seconds}s，报告{report_path}")
    for fail_result in fail_results:
        logger.error(f"失败: {fail_result['pdf_path']} {fail_result['error']}")


def set_log_format():
    for handler in logger.handlers:
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - [%(threadName)s] %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        ))


def parse_args():
    parser = argparse.ArgumentParser(description="批量导入PDF到知识库")
    parser.add_argument("--pdf-dir", default=str(ROOT_DIR / "metadata/CedarSeaGoods_KB/pdf"))
    parser.add_argument("--local-dir", default=str(ROOT_DIR / "output"))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="", help="只导入路径中包含该字符串的PDF，例如 06_pet-gifts")
    parser.add_argument("--force", action="store_true", help="忽略已导入记录，全部重新导入")
    return parser.parse_args()


if __name__ == "__main__":
    main()
