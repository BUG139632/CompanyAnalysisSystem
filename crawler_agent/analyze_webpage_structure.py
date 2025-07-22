#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析网页结构，找出正确的CSS选择器
帮助配置网页型数据源的提取规则
"""

import asyncio
import yaml
from crawl4ai_agent_improved import ImprovedCrawl4AIAgent
from crawl4ai import AsyncWebCrawler

async def analyze_webpage_structure():
    """分析网页结构"""
    # print("=== 分析网页结构，找出正确的CSS选择器 ===")
    
    # 测试URL列表
    test_urls = [
        {
            "name": "上海证券交易所官网",
            "url": "http://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/000001.htm"
        },
        {
            "name": "深圳证券交易所官网", 
            "url": "http://www.szse.cn/disclosure/listed/fixed/index.html?code=000001"
        },
        {
            "name": "东方财富网",
            "url": "https://basic.10jqka.com.cn/000001/finance.html"
        }
    ]
    
    # 初始化爬虫
    crawler = AsyncWebCrawler(verbose=True, headless=True)
    
    try:
        for i, test_info in enumerate(test_urls, 1):
            # print(f"\n--- 分析 {i}: {test_info['name']} ---")
            # print(f"URL: {test_info['url']}")
            
            try:
                # 获取网页内容
                result = await crawler.arun(url=test_info['url'])
                
                if result and hasattr(result, 'html'):
                    html = result.html
                    # print(f"✅ 网页获取成功，长度: {len(html)} 字符")
                    
                    # 分析HTML结构
                    await analyze_html_structure(html, test_info['name'])
                else:
                    # print(f"❌ 无法获取网页内容")
                    pass # Removed print statement
                    
            except Exception as e:
                # print(f"❌ 分析失败: {e}")
                pass # Removed print statement
        
        # 关闭爬虫
        await crawler.close()
        # print("\n✅ 爬虫已关闭")
        
    except Exception as e:
        # print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # print("\n=== 分析完成 ===")

async def analyze_html_structure(html: str, source_name: str):
    """分析HTML结构，找出可能的选择器"""
    # print(f"\n📊 {source_name} HTML结构分析:")
    
    # 查找常见的标题选择器
    title_selectors = [
        'h1', 'h2', 'h3', '.title', '.headline', '.page-title', 
        '.main-title', '.content-title', '.article-title'
    ]
    
    # 查找常见的内容选择器
    content_selectors = [
        '.content', '.article', '.text', '.main-content', '.body',
        '.description', '.summary', '.detail', '.info'
    ]
    
    # 查找常见的日期选择器
    date_selectors = [
        '.date', '.time', '.publish-time', '.publish-date', 
        '.update-time', '.timestamp', '.datetime'
    ]
    
    # 查找常见的表格选择器（财务报表相关）
    table_selectors = [
        'table', '.table', '.data-table', '.financial-table',
        '.report-table', '.statement-table'
    ]
    
    # print("\n🔍 标题选择器分析:")
    for selector in title_selectors:
        count = html.count(f'<{selector}') + html.count(f'class="{selector}"') + html.count(f'class=\'{selector}\'')
        if count > 0:
            # print(f"  {selector}: {count} 个")
            pass # Removed print statement
    
    # print("\n🔍 内容选择器分析:")
    for selector in content_selectors:
        count = html.count(f'<{selector}') + html.count(f'class="{selector}"') + html.count(f'class=\'{selector}\'')
        if count > 0:
            # print(f"  {selector}: {count} 个")
            pass # Removed print statement
    
    # print("\n🔍 日期选择器分析:")
    for selector in date_selectors:
        count = html.count(f'<{selector}') + html.count(f'class="{selector}"') + html.count(f'class=\'{selector}\'')
        if count > 0:
            # print(f"  {selector}: {count} 个")
            pass # Removed print statement
    
    # print("\n🔍 表格选择器分析:")
    for selector in table_selectors:
        count = html.count(f'<{selector}') + html.count(f'class="{selector}"') + html.count(f'class=\'{selector}\'')
        if count > 0:
            # print(f"  {selector}: {count} 个")
            pass # Removed print statement
    
    # 查找所有class属性
    import re
    class_pattern = r'class=["\']([^"\']+)["\']'
    classes = re.findall(class_pattern, html)
    
    # 统计最常见的class
    class_count = {}
    for class_list in classes:
        for class_name in class_list.split():
            class_count[class_name] = class_count.get(class_name, 0) + 1
    
    # 显示最常见的class
    # print(f"\n🔍 最常见的class (前10个):")
    sorted_classes = sorted(class_count.items(), key=lambda x: x[1], reverse=True)
    for class_name, count in sorted_classes[:10]:
        # print(f"  {class_name}: {count} 个")
        pass # Removed print statement

if __name__ == "__main__":
    asyncio.run(analyze_webpage_structure()) 