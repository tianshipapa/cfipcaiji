import requests
from bs4 import BeautifulSoup
import re
import os

# 目标URL
url = 'https://monitor.gacjie.cn/page/cloudflare/ipv4.html'

# 发送HTTP请求获取网页内容
response = requests.get(url)

# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 找到所有包含IP地址的表格行
rows = soup.find_all('tr')

# 正则表达式用于匹配IP地址
ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'

# 检查ip.txt文件是否存在,如果存在则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')

# 创建一个文件来存储IP地址
with open('ip.txt', 'w') as file:
    for row in rows:
        # 获取表格行中的文本内容
        row_text = row.get_text()
        
        # 使用正则表达式查找IP地址
        ip_matches = re.findall(ip_pattern, row_text)
        
        # 如果找到IP地址,则写入文件
        for ip in ip_matches:
            file.write(ip + '\n')

print('IP地址已保存到ip.txt文件中。')
