import requests
from bs4 import BeautifulSoup
import re
import os

# 目标URL列表
urls = [
    'https://ip.164746.xyz', 
    'https://cf.090227.xyz', 
    'https://stock.hostmonit.com/CloudFlareYes',
    'https://www.wetest.vip/page/cloudflare/address_v4.html'  # 修正了链接中的一个拼写错误
]

# 正则表达式用于匹配IP地址
ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

# 检查ip.txt文件是否存在,如果存在则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')

# 创建一个文件来存储IP地址
with open('ip.txt', 'w') as file:
    for url in urls:
        try:
            # 发送HTTP请求获取网页内容
            response = requests.get(url, timeout=5)  # 设置超时时间
            
            # 确保请求成功
            if response.status_code == 200:
                # 获取网页的文本内容
                html_content = response.text
                
                # 使用正则表达式直接在HTML内容中查找IP地址
                ip_matches = re.findall(ip_pattern, html_content, re.IGNORECASE)
                
                # 如果找到IP地址,则写入文件
                for ip in ip_matches:
                    file.write(ip + '\n')
        except requests.exceptions.RequestException as e:
            # 如果请求失败，打印错误信息并继续执行
            print(f'请求 {url} 失败: {e}')
            continue

print('IP地址已保存到ip.txt文件中。')
