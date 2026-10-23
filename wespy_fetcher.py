#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量化的文章抓取器
支持微信公众号、网易、掘金等多种网站，输出结构包含 title、content_text、content_html、content_markdown、url。
"""
import re
import os
import requests
from bs4 import BeautifulSoup, NavigableString

# 模拟浏览器请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def html_to_markdown(html_content: str) -> str:
    """将 HTML 内容转换为 Markdown，保留图片在原文位置"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    result_lines = []
    
    def process_element(element, list_depth=0):
        """递归处理 HTML 元素，转换为 Markdown"""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                return text
            return ""
        
        if element.name is None:
            return ""
        
        tag = element.name.lower()
        
        # 跳过脚本和样式
        if tag in ['script', 'style', 'noscript']:
            return ""
        
        # 处理图片
        if tag == 'img':
            src = element.get('data-src') or element.get('src') or ''
            alt = element.get('alt', '')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                return f"\n\n![{alt}]({src})\n\n"
            return ""
        
        # 处理换行
        if tag == 'br':
            return "\n"
        
        # 处理段落
        if tag == 'p':
            inner = process_children(element, list_depth)
            if inner.strip():
                return f"\n\n{inner.strip()}\n\n"
            return ""
        
        # 处理标题
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            inner = process_children(element, list_depth).strip()
            if inner:
                return f"\n\n{'#' * level} {inner}\n\n"
            return ""
        
        # 处理粗体
        if tag in ['strong', 'b']:
            inner = process_children(element, list_depth).strip()
            if inner:
                return f"**{inner}**"
            return ""
        
        # 处理斜体
        if tag in ['em', 'i']:
            inner = process_children(element, list_depth).strip()
            if inner:
                return f"*{inner}*"
            return ""
        
        # 处理链接
        if tag == 'a':
            href = element.get('href', '')
            inner = process_children(element, list_depth).strip()
            if inner and href:
                return f"[{inner}]({href})"
            return inner
        
        # 处理列表
        if tag == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                item_text = process_children(li, list_depth + 1).strip()
                if item_text:
                    items.append(f"{'  ' * list_depth}- {item_text}")
            if items:
                return "\n\n" + "\n".join(items) + "\n\n"
            return ""
        
        if tag == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                item_text = process_children(li, list_depth + 1).strip()
                if item_text:
                    items.append(f"{'  ' * list_depth}{i}. {item_text}")
            if items:
                return "\n\n" + "\n".join(items) + "\n\n"
            return ""
        
        # 处理代码块
        if tag == 'pre':
            code = element.find('code')
            if code:
                code_text = code.get_text()
                return f"\n\n```\n{code_text}\n```\n\n"
            return f"\n\n```\n{element.get_text()}\n```\n\n"
        
        if tag == 'code':
            inner = element.get_text()
            if inner:
                return f"`{inner}`"
            return ""
        
        # 处理引用
        if tag == 'blockquote':
            inner = process_children(element, list_depth).strip()
            if inner:
                lines = inner.split('\n')
                quoted = '\n'.join(f"> {line}" for line in lines if line.strip())
                return f"\n\n{quoted}\n\n"
            return ""
        
        # 处理表格
        if tag == 'table':
            return process_table(element)
        
        # 处理 div 和 section
        if tag in ['div', 'section', 'article', 'span', 'font']:
            return process_children(element, list_depth)
        
        return process_children(element, list_depth)
    
    def process_children(element, list_depth=0):
        parts = []
        for child in element.children:
            part = process_element(child, list_depth)
            if part:
                parts.append(part)
        return ''.join(parts)
    
    def process_table(table):
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for cell in tr.find_all(['th', 'td']):
                cell_text = cell.get_text(strip=True)
                cells.append(cell_text)
            if cells:
                rows.append(cells)
        
        if not rows:
            return ""
        
        result = "\n\n"
        if rows:
            result += "| " + " | ".join(rows[0]) + " |\n"
            result += "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
            for row in rows[1:]:
                result += "| " + " | ".join(row) + " |\n"
        result += "\n"
        return result
    
    markdown = process_element(soup)
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = markdown.strip()
    
    return markdown


def render_with_playwright(url: str, timeout: int = 30) -> str:
    """使用 Playwright 渲染页面（用于 JS 动态加载的页面）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[警告] Playwright 未安装，无法渲染 JS 页面")
        print("       安装命令: pip install playwright && playwright install chromium")
        return None
    
    browser = None
    try:
        print(f"[渲染] 使用 Playwright 渲染页面（超时 {timeout}秒）...")
        
        with sync_playwright() as p:
            # 启动浏览器，添加反检测配置
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',  # 反检测
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            
            # 创建上下文，模拟真实浏览器
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
            )
            
            page = context.new_page()
            
            # 注入反检测脚本
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page.set_default_timeout(timeout * 1000)
            
            try:
                page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
                # 等待页面内容加载
                page.wait_for_timeout(3000)  # 额外等待 3 秒让 JS 执行
            except Exception as e:
                print(f"[渲染] 页面加载: {e}")
            
            html = page.content()
            browser.close()
            browser = None
            return html
            
    except Exception as e:
        print(f"[警告] Playwright 渲染失败: {e}")
        return None
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass


def fetch_wechat_article(url: str):
    """抓取文章内容（支持微信、网易、掘金等多种网站）"""
    if not url:
        print(f"[错误] URL 为空")
        return None
    
    try:
        print(f"[抓取中] 正在请求: {url}")
        
        # 根据域名选择不同的处理方式
        if 'mp.weixin.qq.com' in url:
            return fetch_wechat(url)
        elif '163.com' in url or 'ds.163.com' in url:
            return fetch_163(url)
        elif 'juejin.cn' in url:
            return fetch_juejin(url)
        else:
            return fetch_generic(url)
            
    except requests.exceptions.Timeout:
        print(f"[错误] 请求超时: {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[错误] 网络连接失败: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[错误] HTTP 错误: {e}")
        return None
    except Exception as e:
        print(f"[错误] 未知异常: {type(e).__name__}: {e}")
        return None


def fetch_wechat(url: str):
    """抓取微信公众号文章"""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://mp.weixin.qq.com/'
    
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 提取标题
    title_tag = (
        soup.find('h1', class_='rich_media_title') or 
        soup.find('h2', class_='rich_media_title') or
        soup.find('title') or 
        soup.find('h1')
    )
    title = title_tag.get_text(strip=True) if title_tag else '未知标题'
    print(f"[成功] 标题: {title[:50]}...")
    
    # 提取正文
    content_elem = (
        soup.find(id='js_content') or 
        soup.find(class_='rich_media_content') or 
        soup.find('article')
    )
    
    content_html = str(content_elem) if content_elem else ''
    content_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
    content_markdown = html_to_markdown(content_html) if content_html else ''
    
    return {
        'title': title,
        'content_html': content_html,
        'content_text': content_text,
        'content_markdown': content_markdown,
        'url': url,
    }


def fetch_163(url: str):
    """抓取网易文章（包括网易大神社区）"""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://www.163.com/'
    
    # 先尝试普通抓取
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 提取标题
    title_tag = (
        soup.find('h1', class_='article-title') or
        soup.find('h1', class_='title') or
        soup.find('div', class_='article-title') or
        soup.find('h1') or 
        soup.find('title')
    )
    title = title_tag.get_text(strip=True) if title_tag else '未知标题'
    # 清理标题
    title = title.replace('_网易新闻', '').replace('_网易', '').replace(' - 网易', '').strip()
    title = title.replace('_游戏热爱者兴趣圈_游戏社区', '').strip()
    
    # 提取正文（网易大神社区多种选择器）
    content_elem = (
        soup.find('div', class_='article-content') or
        soup.find('div', class_='article-body') or
        soup.find('div', class_='post-content') or
        soup.find('div', class_='post_body') or
        soup.find('div', class_='content') or
        soup.find('article') or
        soup.find('div', id='content')
    )
    
    # 如果没找到，尝试查找包含最多段落的元素
    if not content_elem or len(content_elem.get_text(strip=True)) < 100:
        all_p = soup.find_all('p')
        if all_p:
            parent_counts = {}
            for p in all_p:
                parent = p.parent
                if parent and parent.name in ['div', 'article', 'section']:
                    parent_counts[parent] = parent_counts.get(parent, 0) + 1
            if parent_counts:
                content_elem = max(parent_counts.items(), key=lambda x: x[1])[0]
    
    content_html = str(content_elem) if content_elem else ''
    content_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
    
    # 如果内容太少，尝试 Playwright 渲染
    if len(content_text) < 100:
        print("[检测] 普通抓取内容较少，尝试 Playwright 渲染...")
        html = render_with_playwright(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 重新提取标题
            title_tag = (
                soup.find('h1', class_='article-title') or
                soup.find('h1', class_='title') or
                soup.find('div', class_='article-title') or
                soup.find('h1') or 
                soup.find('title')
            )
            if title_tag:
                title = title_tag.get_text(strip=True)
                title = title.replace('_网易新闻', '').replace('_网易', '').replace(' - 网易', '').strip()
                title = title.replace('_游戏热爱者兴趣圈_游戏社区', '').strip()
            
            # 重新提取正文
            content_elem = (
                soup.find('div', class_='article-content') or
                soup.find('div', class_='article-body') or
                soup.find('div', class_='post-content') or
                soup.find('div', class_='post_body') or
                soup.find('div', class_='content') or
                soup.find('article') or
                soup.find('div', id='content')
            )
            
            if not content_elem or len(content_elem.get_text(strip=True)) < 100:
                all_p = soup.find_all('p')
                if all_p:
                    parent_counts = {}
                    for p in all_p:
                        parent = p.parent
                        if parent and parent.name in ['div', 'article', 'section']:
                            parent_counts[parent] = parent_counts.get(parent, 0) + 1
                    if parent_counts:
                        content_elem = max(parent_counts.items(), key=lambda x: x[1])[0]
            
            content_html = str(content_elem) if content_elem else ''
            content_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
    
    print(f"[成功] 标题: {title[:50]}...")
    
    content_markdown = html_to_markdown(content_html) if content_html else ''
    
    # 如果内容还是太少，获取整个 body
    if len(content_text) < 100:
        print("[警告] 内容较少，尝试获取更多...")
        body = soup.find('body')
        if body:
            for tag in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            content_text = body.get_text(separator='\n', strip=True)
            if not content_markdown:
                content_markdown = content_text
    
    return {
        'title': title,
        'content_html': content_html,
        'content_text': content_text,
        'content_markdown': content_markdown,
        'url': url,
    }


def fetch_juejin(url: str):
    """抓取掘金文章"""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://juejin.cn/'
    
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 掘金可能需要 JS 渲染
    if re.search(r'未开启.*Javascript|Javascript运行', resp.text, re.I):
        print("[检测] 页面需要 JS 渲染，尝试 Playwright...")
        html = render_with_playwright(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
    
    # 提取标题
    title_tag = (
        soup.find('h1', class_='article-title') or
        soup.find('h1', class_='article-title-text') or
        soup.find('h1') or
        soup.find('title')
    )
    title = title_tag.get_text(strip=True) if title_tag else '未知标题'
    print(f"[成功] 标题: {title[:50]}...")
    
    # 提取正文
    content_elem = (
        soup.find('div', id='article-root') or
        soup.find('div', class_='article-content') or
        soup.find('div', class_='markdown-body') or
        soup.find('article')
    )
    
    content_html = str(content_elem) if content_elem else ''
    content_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
    content_markdown = html_to_markdown(content_html) if content_html else ''
    
    return {
        'title': title,
        'content_html': content_html,
        'content_text': content_text,
        'content_markdown': content_markdown,
        'url': url,
    }


def fetch_generic(url: str):
    """抓取通用网页文章"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    # 检测编码
    if resp.encoding == 'ISO-8859-1':
        resp.encoding = resp.apparent_encoding or 'utf-8'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 检查是否需要 JS 渲染
    if re.search(r'未开启.*Javascript|Javascript运行|enable.*javascript', resp.text, re.I):
        print("[检测] 页面需要 JS 渲染，尝试 Playwright...")
        html = render_with_playwright(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
    
    # 提取标题
    title_tag = (
        soup.find('title') or 
        soup.find('h1') or 
        soup.find('h2') or
        soup.find('meta', {'property': 'og:title'})
    )
    if title_tag:
        if title_tag.name == 'meta':
            title = title_tag.get('content', '').strip()
        else:
            title = title_tag.get_text(strip=True)
    else:
        title = '未知标题'
    
    print(f"[成功] 标题: {title[:50]}...")
    
    # 提取正文（多种选择器）
    content_selectors = [
        'article',
        '.article-content',
        '.content',
        '.post-content',
        '.entry-content',
        '#content',
        '.main-content',
        'main'
    ]
    
    content_elem = None
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem and len(content_elem.get_text(strip=True)) > 100:
            break
    
    if not content_elem:
        content_elem = soup.find('body')
    
    content_html = str(content_elem) if content_elem else ''
    content_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
    content_markdown = html_to_markdown(content_html) if content_html else ''
    
    return {
        'title': title,
        'content_html': content_html,
        'content_text': content_text,
        'content_markdown': content_markdown,
        'url': url,
    }