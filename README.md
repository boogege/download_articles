# download_articles

微信公众号文章批量下载工具，独立 Python 脚本，将公众号文章保存为 Markdown 文件并自动下载内嵌图片。

> 
> ⚠️ 说明：本工具仅用于个人学习、本地归档，请勿用于商用、大规模爬虫或侵权分发，请尊重原文作者版权。

## ✨ 功能特性

- 支持在脚本内配置链接，或者命令行传入多个文章链接
- 每篇文章单独创建文件夹，Markdown 文件 + 图片放在一起
- 自动提取文章内图片并下载，按顺序命名 `img_001.jpg`
- 自动去重检测：MD 文件头部记录原文链接，重复链接自动跳过
- 标题自动清洗，过滤 Windows 非法文件名字符，超长标题截断
- 同名文件夹自动加后缀，避免覆盖旧文件
- 兼容 Markdown 图片语法、微信 `img` 标签 `src` / `data-src`

## 📁 目录结构示例

```
download_articles/
├── download_articles.py
├── wespy_fetcher.py
├── LICENSE
├── README.md
├── 这是一篇公众号文章/
│   ├── 这是一篇公众号文章.md
│   ├── img_001.jpg
│   ├── img_002.png
└── 另一篇文章_1/
    ├── 另一篇文章.md
    └── img_001.webp
```

## 📌 依赖要求

- Python 3.6+
- `wespy_fetcher.py` 必须和本脚本放在**同一目录**（核心抓取模块）

## 🚀 使用方法

### 方式 1：脚本内预先配置链接

打开 `download_articles.py`，修改配置区的 `STYLE_ARTICLE_URLS`

```
STYLE_ARTICLE_URLS = [
    "https://mp.weixin.qq.com/s/xxxxxxxxxx",
    "https://mp.weixin.qq.com/s/yyyyyyyyyy"
]
```

运行脚本：

```
python download_articles.py
```

### 方式 2：命令行临时传入链接

```
python download_articles.py "链接1" "链接2"
```

## 📄 输出 Markdown 格式

生成的 md 文件自带头部信息：

```
# 文章标题

> 原文链接：https://mp.weixin.qq.com/s/xxxxxx

文章正文内容...
```

## ⚙️ 配置说明

- `STYLE_DIR`：输出根目录，默认是脚本所在文件夹
- `slugify`：标题转文件名规则，过滤特殊符号，最长保留 50 字符
- 重复判断逻辑：递归检索所有 `.md` 文件头部是否包含目标 URL

## ⚠️ 注意事项

1. **抓取依赖 `wespy_fetcher.py`**，缺少该文件会抓取失败
2. 微信图片存在防盗链，部分图片可能下载失败，属于正常现象
3. 不支持需要登录、付费阅读、已删除、设置访问限制的文章
4. 仅用于个人本地备份，禁止未经授权批量采集、二次分发

## 📜 License

MIT License
