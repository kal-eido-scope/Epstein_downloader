import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import HTTPError
from requests import Session
from src.config import LOG_DIR, BASE_DIR, init_logger
import json
from pathlib import Path
import time

class FileDownloader():
    def __init__(self, session: Session, dir_path:str|Path, max_workers: int = 6, max_retry_times: int = 3, page_dir:str|Path = None, **kwargs):
        self.session = session
        self.max_workers = max_workers
        self.max_retry_times = max_retry_times
        self.logger = init_logger('downloader', LOG_DIR / 'file_download.log')
        self.file_dir = Path(dir_path)
        self.file_dir.mkdir(parents=True, exist_ok=True)
        self.page_dir = Path(page_dir) if page_dir else None
        
    def download_file(self, url: str, file_path: Path, max_retry_times:int = 3) -> tuple[str, str, str]:
        """下载单个文件，支持断点续传和重试机制"""
        for retry_time in range(1, max_retry_times + 1):
            reason_list: list[str] = []
            try:
                existing_size = file_path.stat().st_size if file_path.exists() else 0
                request_headers = {}
                
                if existing_size > 0:
                    request_headers["Range"] = f"bytes={existing_size}-"

                resp = self.session.get(url, stream=True, timeout=20, headers=request_headers)
                
                if resp.status_code == 416:
                    self.logger.info(f"下载完成: {url}")
                    return url, "success", ""
                resp.raise_for_status()
                expected = int(resp.headers.get("content-length", 0))
                bytes_written = 0
                if resp.status_code == 206 and expected > 0:
                    mode = "ab"
                else:
                    mode = "wb"

                if mode == "wb" and existing_size > 0:
                    existing_size = 0
                
                with open(file_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)
                if expected and bytes_written != expected:
                    raise IOError(f"(已下载 {bytes_written} bytes , 剩余{expected - bytes_written}bytes未下载完成)")
                if expected and resp.status_code == 206:
                    total = existing_size + bytes_written
                    if total != existing_size + expected:
                        raise IOError(f"(已下载 {total} bytes , 剩余{existing_size + expected - total}bytes未下载完成)")
                self.logger.info(f"下载完成: {url}")
                return url, "success", ""
            except HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                if status_code:
                    reason = f"http {status_code}"
                else:
                    reason = str(e)
                reason_list.append(reason)
                self.logger.warning(f"重试第{retry_time}次/总{max_retry_times}次失败 : {url}: {reason}")
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass
                time.sleep(2 * retry_time)
            except Exception as e:
                reason = str(e)
                reason_list.append(reason)
                self.logger.warning(f"重试第{retry_time}次/总{max_retry_times}次失败 : {url}: {reason}")
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass
                time.sleep(2 * retry_time)
        self.logger.error(f"下载失败: {url}，重试次数: {max_retry_times}, 原因: {', '.join(reason_list)}")
        return url, "failed", reason_list
        
    def start_download(self, data_set_number: int):
        """开始下载数据集中的文件，使用多线程并发下载，记录下载结果"""
        status_report: dict[str, dict[str, str]] = {}
        status_lock = threading.Lock()
        scheduled_urls: set[str] = set()
        try:
            with open(self.page_dir / f"data-set-{data_set_number}" / f"dataset{data_set_number}_file_links.json", 'r') as f:
                data: dict[str, list[str]] = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"数据集 {data_set_number} 的文件——链接JSON文件未找到，无法开始下载。请先运行page命令下载并提取链接。")
            return

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            future_to_output: dict = {}
            for page, link_list in data.items():
                output_path = self.file_dir / f"data-set-{data_set_number}" / f"page_{page}"
                output_path.mkdir(parents=True, exist_ok=True)
                if output_path.is_relative_to(BASE_DIR):
                    output_key = output_path.relative_to(BASE_DIR).as_posix()
                else:
                    output_key = output_path.as_posix()
                status_report.setdefault(output_key, {})
                for link in link_list:
                    if link in scheduled_urls:
                        with status_lock:
                            status_report[output_key][link] = "skipped (duplicate)"
                        continue
                    scheduled_urls.add(link)
                    filename = link.split("/")[-1]
                    file_path = output_path / filename
                    future = executor.submit(self.download_file, link, file_path)
                    futures.append(future)
                    future_to_output[future] = output_key

            for future in as_completed(futures):
                url, status, reason = future.result()
                output_key = future_to_output.get(future, "")
                if output_key:
                    with status_lock:
                        status_report.setdefault(output_key, {})
                        if status == "success":
                            status_report[output_key][url] = "success"
                        else:
                            status_report[output_key][url] = f"failed: {reason}"

        report_path = self.file_dir / f"data-set-{data_set_number}" / "downloads_status.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(status_report, f, ensure_ascii=False, indent=2)
            
    def retry_failed_downloads(self, data_set_number: int):
        """重试下载失败的文件，更新下载结果"""
        status_json_path = self.file_dir / f"data-set-{data_set_number}" / "downloads_status.json"
        try:
            with open(status_json_path, "r", encoding="utf-8") as f:
                failed_dict: dict[str, dict[str, str]] = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"数据集 {data_set_number} 的下载状态JSON文件未找到，无法重试下载。请先运行start_download方法开始下载。")
            return
        failed_again = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            future_to_folder: dict = {}
            for folder, status_dict in failed_dict.items():
                for url, status in status_dict.items():
                    if not isinstance(status, str) or not status.startswith("failed"):
                        continue
                    output_dir = Path(folder)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = url.split("/")[-1]
                    file_path = output_dir / filename
                    future = executor.submit(self.download_file, url, file_path)
                    futures.append(future)
                    future_to_folder[future] = folder

            for future in as_completed(futures):
                failed_url = future.result()
                if failed_url:
                    folder = future_to_folder.get(future, "")
                    failed_again.setdefault(folder, {})
                    failed_again[folder][failed_url] = "failed: retry failed"

        if failed_again:
            with open(status_json_path, "w", encoding="utf-8") as f:
                json.dump(failed_again, f, ensure_ascii=False, indent=2)
