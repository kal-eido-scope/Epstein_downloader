import json
from src.config import PAGE_DIR
from .pagedownloader import logger

def check_repeats(id:int):
    with open(PAGE_DIR / f"data-set-{id}/dataset{id}_file_links.json","r") as f:
        data:dict[str:list[str]] = json.load(f)
    all_value_list = []
    for new_links in data.values():
        for new_link in new_links:
            all_value_list.append(new_link)
    logger.info(f"总链接数{len(all_value_list)}, 去重后链接数{len(set(all_value_list))}, 重复链接数{len(all_value_list)-len(set(all_value_list))}")
    logger.info("重复链接在下载中将跳过")
