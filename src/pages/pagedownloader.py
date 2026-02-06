from requests import Response, Session
import re
from src.config import init_logger, LOG_DIR
import random
import time
import json
from pathlib import Path
import hashlib

logger = init_logger('dataset_downloader', LOG_DIR / "page_analyze.log")
class PageDownloader:
    """负责下载数据集的原始网页内容并提取文件链接"""
    def __init__(self,session:Session,
                 base_url:str,
                 dir_path:str|Path,
                 max_retry_times:int=7,
                 max_repeat_pages:int=5,
                 pattern = None,
                 **kwargs
                 ):
        self.session = session
        self.data_set_number = -1
        self.base_url = base_url
        self.dir_path = Path(dir_path)
        self.pattern = pattern
        self.max_retry_times = max_retry_times
        self.max_repeat_pages = max_repeat_pages
        
        self.retry_times = 0
        self.failed_pages = []
        self.file_link_dict = {}       
    
    def random_sleep(self):
        """随机休眠"""
        # time.sleep(random.uniform(1, 6))
        time.sleep(0.3)

    def backoff_sleep(self, attempt:int, base:float = 3.0, cap:float = 60.0):
        """退避等待，指数休眠"""
        delay = min(cap, base * (2 ** (attempt - 1)))
        rd_delay = random.uniform(0, delay * 0.3)
        time.sleep(delay + rd_delay)

    def _hash_links(self, links:list[str]) -> str:
        joined = "\n".join(links)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def warmup_session(self):
        """预热会话"""
        try:
            resp = self.session.get(self.base_url, timeout=10)
            resp.cookies.update(self.session.cookies)
        except Exception:
            pass
        
    def make_request(self,url:str, max_attempts:int = 3) -> Response | None:
        """带重试地发送httpGET"""
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code in (403, 429):
                    logger.warning(f"{url} 返回 {resp.status_code}，第 {attempt}/{max_attempts} 次尝试，退避等待后重试。")
                    self.backoff_sleep(attempt, base=5.0, cap=90.0)
                    continue
                resp.raise_for_status()
                return resp
            except Exception as e:
                logger.error(f"{url} 请求失败(第 {attempt}/{max_attempts} 次): {e}")
                if attempt < max_attempts:
                    self.backoff_sleep(attempt)
        return None
    
    def re_findall_files(self,text:str)->list[str]:
        """使用正则表达式提取文件链接"""
        pattern = re.compile(self.pattern) if self.pattern else re.compile(r'href="(https:\/\/[w]{3}\.justice\.gov\/epstein\/files\/DataSet[^"]+)"')
        links = pattern.findall(text)
        # full_links = [f"https://www.justice.gov{link}" for link in links]
        return links
            
    def download_original_webpage(self,data_set_number:int, start_page:int|None=None,max_pages:int|None=None):
        """下载数据集的原始网页内容并使用regex提取文件链接"""
        self.data_set_number = data_set_number
        self.data_set_url = f"{self.base_url}/data-set-{data_set_number}-files"
        self.output_dir = self.dir_path / f"data-set-{data_set_number}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.warmup_session()
        cur_page = start_page or 0
        try:
            repeat_pages = 0
            last_links_hash = None
            while True:
                if max_pages is not None and cur_page > max_pages:
                    logger.info(f"数据集 {self.data_set_number} 达到最大页码限制 {max_pages}，停止提取。")
                    break
                page_url = f"{self.data_set_url}?page={cur_page}"
                resp = self.make_request(page_url)
                if resp:
                    file_links = self.re_findall_files(resp.text)

                    current_hash = self._hash_links(file_links)
                    if last_links_hash == current_hash:
                        repeat_pages += 1
                        logger.info(f"数据集 {self.data_set_number} 页码 {cur_page} 与上一页内容一致, 连续重复: {repeat_pages}.")
                    else:
                        repeat_pages = 0
                    last_links_hash = current_hash

                    self.file_link_dict[cur_page] = file_links
                    logger.info(f"已处理数据集 {self.data_set_number} 的第 {cur_page} 页, 提取到 {len(file_links)} 个文件链接.")

                    if repeat_pages >= self.max_repeat_pages:
                        logger.info(f"数据集 {self.data_set_number} 重复页达到阈值，停止提取。")
                        break
                else:
                    logger.info(f"数据集 {self.data_set_number} 页码 {cur_page} 请求失败。")
                    self.failed_pages.append(cur_page)
                cur_page += 1
                self.random_sleep()
            if self.failed_pages:
                logger.info(f"数据集 {self.data_set_number} 以下页码请求失败: {self.failed_pages}")
                self.retry_pages()
        except Exception as e:
            logger.error(f"数据集 {self.data_set_number} 下载过程中发生错误: {e}")
        except KeyboardInterrupt:
            logger.warning(f"数据集 {self.data_set_number} 下载被用户中断。")
        finally:
            self.write_links_to_file()
            if self.failed_pages:
                self.write_failed_pages_to_file()
    
    def retry_pages(self):
        """重试下载失败的页码"""
        while self.failed_pages and self.retry_times <= self.max_retry_times:
            logger.info(f"开始重试数据集 {self.data_set_number} 失败的页码: {self.failed_pages}, 当前重试次数: {self.retry_times}")
            current_failed = list(self.failed_pages)
            self.failed_pages = []
            for page in current_failed:
                page_url = f"{self.data_set_url}?page={page}"
                resp = self.make_request(page_url)
                if resp:
                    file_links = self.re_findall_files(resp.text)
                    self.file_link_dict[page] = file_links
                    logger.info(f"重试成功: 数据集 {self.data_set_number} 页码 {page}, 提取到 {len(file_links)} 个文件链接.")
                else:
                    logger.error(f"重试失败: 数据集 {self.data_set_number} 页码 {page}.")
                    self.failed_pages.append(page)
                self.random_sleep()
            self.retry_times += 1

        if self.failed_pages:
            self.write_failed_pages_to_file()
            logger.error(f"重试次数超过最大限制 {self.max_retry_times}，停止重试, 剩余失败页码: {self.failed_pages}")
        else:
            logger.info(f"所有失败页码已重试成功，无需继续重试。")
    
    
    def write_links_to_file(self):
        """将提取的文件链接写入JSON文件"""
        data = self.file_link_dict
        sorted_dict = dict(sorted(data.items(), key=lambda item: int(item[0])))
        with open(self.output_dir / f"dataset{self.data_set_number}_file_links.json", "w") as f:
            json.dump(sorted_dict, f, indent=4)
            
    def write_failed_pages_to_file(self):
        """将失败的页码写入文本文件"""
        with open(self.output_dir / f"dataset{self.data_set_number}_failed_pages.txt", "w") as f:
            f.write(",".join(map(str, self.failed_pages)))
            
    @classmethod
    def retry_page_list(cls,failed_pages:list[int], session: Session, base_url: str,
                        data_set_number: int, output_dir: str|Path,
                        max_retry_times:int=7, max_repeat_pages:int=8):
        """类方法：单独重试失败的页码列表"""
        downloader = cls(session,base_url,data_set_number,output_dir,max_retry_times=max_retry_times,max_repeat_pages=max_repeat_pages)
        downloader.failed_pages = failed_pages
        downloader.retry_pages()
        return downloader.file_link_dict
