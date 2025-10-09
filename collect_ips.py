import requests
from bs4 import BeautifulSoup
import re
import os

# 目标URL列表
urls = [
    'https://ip.164746.xyz', 
    'https://cf.090227.xyz', 
    'https://stock.hostmonit.com/CloudFlareYes',
    'https://www.wetest.vip/page/cloudflare/address_v4.html'
]

# 正则表达式用于匹配IP地址
ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

# 检查ip.txt文件是否存在,如果存在则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')

# 使用集合存储IP地址实现自动去重
unique_ips = set()

for url in urls:
    try:
        # 发送HTTP请求获取网页内容
        response = requests.get(url, timeout=5)
        
        # 确保请求成功
        if response.status_code == 200:
            # 获取网页的文本内容
            html_content = response.text
            
            # 使用正则表达式查找IP地址
            ip_matches = re.findall(ip_pattern, html_content, re.IGNORECASE)
            
            # 将找到的IP添加到集合中（自动去重）
            unique_ips.update(ip_matches)
    except requests.exceptions.RequestException as e:
        print(f'请求 {url} 失败: {e}')
        continue

# 将去重后的IP地址按数字顺序排序后写入文件
if unique_ips:
    # 按IP地址的数字顺序排序（非字符串顺序）
    sorted_ips = sorted(unique_ips, key=lambda ip: [int(part) for part in ip.split('.')])
    
    with open('ip.txt', 'w') as file:
        for ip in sorted_ips:
            file.write(ip + '\n')
    print(f'已保存 {len(sorted_ips)} 个唯一IP地址到ip.txt文件。')
else:
    print('未找到有效的IP地址。')
