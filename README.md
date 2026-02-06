# Epstein_downloader

爬取 U.S. Department of Justice 关于 Epstein 的dataset页面中的文件链接并批量保存。

## 特性

- 正则提取，并发下载
- 运行结果以 JSON 写入 `pages/data-set-*`，同时记录失败页与运行日志

## 快速开始

0. python版本

```bash
python==3.11.11  # 不过别的版本应该问题不大。
```

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 抓取页面链接（示例：抓取第 1- 2 个数据集）：

```bash
python main.py page --start 1 --end 2
```

3. 下载文件（示例：下载数据集 6 的文件）：

```bash
python main.py file --start 6
```

| 命令 | 参数       | 说明                                               |
| ---- | ---------- | -------------------------------------------------- |
| page | -s/--start | 根据网页分析其中的下载链接，设置起始数据集         |
| page | -e/--end   | 设置结束数据集，不设置时默认只爬取--start单数据集  |
| file | -s/--start | 下载某数据集的文件文件，设置起始数据集             |
| file | -e/--end   | 设置结束数据集，不设置时默认只爬取--start单数据集  |
| file | -r/--retry | flag，设置时仅根据运行记录对失败的下载进行一次重试 |

## 配置

- 可通过根目录 `.env` 或环境变量进行覆盖

## 目录概览

- `main.py`：入口（命令：`page` / `file`）
- `src/pages`：爬页面
- `src/files`：文件下载
- `src/config`：配置
- `pages/`：爬页面的结果（含失败输出）
- `files/`：下载文件（含下载结果，`success` / `failed` / `skipped`
- `log/`：运行日志

## 运行建议

1. 不建议将并发数调太高
2. 已将当前爬虫结果放在page文件夹
3. 如果使用page发现爬不到文件链接，可首先考虑正则pattern问题，网站前端链接发生过更改。

## 免责声明

请在合法与合规范围内使用本工具；因爬虫产生的任何后果由使用者自行承担。
