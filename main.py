import argparse
from src.config import get_settings
from src.pages import PageDownloader, check_repeats
from src.files import FileDownloader
from src.config import session

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Epstein DOJ Disclosures Downloader")
    subparsers = parser.add_subparsers(dest="command", required=True, help="可用命令")
    
    parser_page = subparsers.add_parser("page", help="根据网页分析其中的下载链接")
    parser_page.add_argument("-s","--start", type=int, default=1, help="起始页码，默认为1",required=True)
    parser_page.add_argument("-e","--end", type=int, help="结束页码，不指定默认使用起始页码",required=False)
    
    parser_file = subparsers.add_parser("file", help="下载文件")
    parser_file.add_argument("-s","--start", type=int, default=1, help="起始页码，默认为1",required=True)
    parser_file.add_argument("-e","--end", type=int, help="结束页码，不知道默认使用起始页码",required=False)
    parser_file.add_argument("-r","--retry", action="store_true", help="重试下载失败的文件链接")
    
    args = parser.parse_args()
    return args

def main():
    settings = get_settings()
    args = parse_args()
    
    if args.command == "page":
        if args.end is None:
            args.end = args.start
        
        for data_set_number in range(args.start, args.end + 1):
            downloader = PageDownloader(session=session, 
                                        **settings.PAGE.model_dump())
            downloader.download_original_webpage(data_set_number)
            check_repeats(data_set_number)
    
    if args.command == "file":
        if args.end is None:
            args.end = args.start
        
        for data_set_number in range(args.start, args.end + 1):
            downloader = FileDownloader(session=session,
                                        page_dir=settings.PAGE.dir_path,
                                        **settings.FILE.model_dump()
                                        )
            if args.retry:
                downloader.retry_failed_downloads(data_set_number=data_set_number)
            else:
                downloader.start_download(data_set_number=data_set_number)

        

if __name__ == "__main__":
    main()