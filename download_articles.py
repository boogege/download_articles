#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立版：下载微信公众号文章

保存位置：脚本所在目录
文件格式：每篇文章一个以标题命名的文件夹，内含 .md 和图片

用法：
1. 直接运行：
   python download_articles.py

2. 命令行传入文章链接：
   python download_articles.py "链接1" "链接2"

依赖：
- wespy_fetcher.py 需要放在同目录，或在 Python 路径中可导入
"""

import sys
import re
import os
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List


# ==================== 配置区 ====================
# 文章链接列表，可直接在这里填写
STYLE_ARTICLE_URLS = [
    # "https://mp.weixin.qq.com/s/xxxxxxxx",
    # "https://mp.weixin.qq.com/s/yyyyyyyy",
]

# 输出目录：脚本所在目录
STYLE_DIR = Path(__file__).resolve().parent
# ================================================


def slugify(text: str) -> str:
    """将标题转换为文件名安全的格式"""
    if not text:
        return "untitled"
    s = text.strip()
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', s)
    s = re.sub(r'[\s]+', '_', s)
    s = s[:50]
    return s or "untitled"


def is_article_exists(url: str, directory: Path) -> bool:
    """检查本地是否已存在相同 URL 的文章"""
    if not directory.exists():
        return False

    # 递归查找子文件夹中的 md 文件
    for md_file in directory.rglob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                head = f.read(500)
            if url in head:
                return True
        except Exception:
            continue
    return False


def fetch_wechat_article(url: str) -> Optional[dict]:
    """尝试使用 wespy_fetcher 抓取文章"""
    errors = []

    try:
        from wespy_fetcher import fetch_wechat_article as wf
        result = wf(url)
        if result and result.get('title') and result.get('content_text'):
            return result
        errors.append("wespy_fetcher: 返回数据不完整")
    except ImportError as e:
        errors.append(f"wespy_fetcher: 模块导入失败 - {e}")
    except Exception as e:
        errors.append(f"wespy_fetcher: {type(e).__name__}: {e}")

    print(f"[错误] 抓取失败: {url}")
    for err in errors:
        print(f"  - {err}")
    return None


def download_image(img_url: str, save_path: Path) -> bool:
    """下载单张图片到指定路径"""
    try:
        req = urllib.request.Request(
            img_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0 Safari/537.36",
                "Referer": "https://mp.weixin.qq.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(save_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  [警告] 图片下载失败: {img_url} -> {e}")
        return False


def guess_ext_from_url(url: str, content_type: str = "") -> str:
    """从 URL 或 Content-Type 推断图片扩展名"""
    # 优先从 URL 的 wx_fmt 参数获取
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "wx_fmt" in qs and qs["wx_fmt"]:
        fmt = qs["wx_fmt"][0].lower()
        if fmt in ("jpeg", "jpg", "png", "gif", "webp", "bmp", "svg"):
            return "jpg" if fmt == "jpeg" else fmt

    # 从路径扩展名获取
    ext = os.path.splitext(parsed.path)[1].lstrip(".").lower()
    if ext in ("jpeg", "jpg", "png", "gif", "webp", "bmp", "svg"):
        return "jpg" if ext == "jpeg" else ext

    # 从 Content-Type 获取
    if content_type:
        if "jpeg" in content_type or "jpg" in content_type:
            return "jpg"
        if "png" in content_type:
            return "png"
        if "gif" in content_type:
            return "gif"
        if "webp" in content_type:
            return "webp"
        if "svg" in content_type:
            return "svg"

    return "jpg"


def extract_image_urls(content: str) -> List[str]:
    """从 md/html 内容中提取所有图片 URL（保持出现顺序、去重）"""
    urls = []
    seen = set()

    # Markdown 语法: ![alt](url)
    for m in re.finditer(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+["\'][^"\']*["\'])?\)', content):
        u = m.group(1).strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    # HTML 标签: <img ... src="url" ...>
    for m in re.finditer(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
        u = m.group(1).strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    # data-src (微信常见)
    for m in re.finditer(r'<img[^>]+data-src\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
        u = m.group(1).strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    return urls


def save_article_images(content: str, article_dir: Path) -> int:
    """独立操作：把文章内容里的图片下载到 article_dir，不修改 content"""
    if not content:
        return 0

    urls = extract_image_urls(content)
    if not urls:
        return 0

    count = 0
    for idx, img_url in enumerate(urls, 1):
        # 跳过已存在的本地路径
        if not img_url.startswith(("http://", "https://")):
            continue

        ext = guess_ext_from_url(img_url)
        filename = f"img_{idx:03d}.{ext}"
        save_path = article_dir / filename

        if download_image(img_url, save_path):
            print(f"  [图片] {filename}")
            count += 1
        else:
            print(f"  [图片失败] {img_url}")

    return count


def run(urls: List[str] = None):
    """执行下载流程"""
    STYLE_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("下载微信公众号文章")
    print("=" * 60)
    print(f"输出目录: {STYLE_DIR}")
    print()

    article_urls = urls or STYLE_ARTICLE_URLS

    if not article_urls:
        print("[提示] 没有配置文章链接")
        print("请在脚本顶部的 STYLE_ARTICLE_URLS 中添加链接，或运行时传入：")
        print('  python download_articles.py "链接1" "链接2"')
        return {"success": False, "error": "没有配置文章链接"}

    success_count = 0
    skip_count = 0

    for url in article_urls:
        if is_article_exists(url, STYLE_DIR):
            print(f"[跳过] 已存在: {url}")
            skip_count += 1
            print()
            continue

        print(f"[抓取中] {url}")
        data = fetch_wechat_article(url)

        if not data:
            print(f"[跳过] 未能抓取")
            print()
            continue

        title = data.get("title", "未知标题")
        print(f"[成功] 标题: {title[:40]}...")

        slug = slugify(title)

        # 以标题命名新建文件夹
        article_dir = STYLE_DIR / slug
        # 若已存在同名文件夹，加后缀避免覆盖
        base_article_dir = article_dir
        suffix = 1
        while article_dir.exists():
            article_dir = base_article_dir.parent / f"{slug}_{suffix}"
            suffix += 1
        article_dir.mkdir(parents=True, exist_ok=True)

        md_path = article_dir / f"{slug}.md"

        content = data.get("content_markdown") or data.get("content_text", "")

        # 步骤1：保存 md 文章（内容原样保存）
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"> 原文链接：{url}\n\n")
            f.write(content)
        print(f"[保存] {article_dir.name}/{slug}.md")

        # 步骤2：独立操作，下载文章中的图片到同一文件夹
        img_count = save_article_images(content, article_dir)
        if img_count:
            print(f"[图片] 共下载 {img_count} 张")

        print()
        success_count += 1

    print("=" * 60)
    print(f"[完成] 成功下载 {success_count} 篇文章")
    if skip_count > 0:
        print(f"[跳过] {skip_count} 篇已存在")
    print(f"目录: {STYLE_DIR}")
    print("=" * 60)

    return {"success": True, "count": success_count, "skipped": skip_count}


if __name__ == '__main__':
    urls = sys.argv[1:] if len(sys.argv) > 1 else None
    run(urls)