#!/usr/bin/env python3
"""
一键可用 / GitHub Actions 实测通过
依赖安装：
    pip install -U requests beautifulsoup4 fake-useragent undetected-chromedriver
"""

import os
import re
import time
import random
import logging
from typing import Set, List

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import undetected_chromedriver as uc

# >>> 1. 驱动版本与 Runner 系统 Chrome 保持一致（140） <<<
os.environ["UC_CHROMEDRIVER_VERSION"] = "140.0.7339.207"

# >>> 2. 日志配置 <<<
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

# >>> 3. 全局常量 <<<
IP_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
OUTPUT_FILE = "ip.txt"
RETRY_TIMES = 3
TIMEOUT = 8
RANDOM_JITTER = (1, 3)  # 随机暂停区间（秒）

URLS = [
    'https://ip.164746.xyz', 
    'https://cf.090227.xyz', 
    'https://stock.hostmonit.com/CloudFlareYes',
    'https://ip.haogege.xyz/',
    'https://ct.090227.xyz',
    'https://cmcc.090227.xyz',    
    'https://cf.vvhan.com',
    'https://api.uouin.com/cloudflare.html',
    'https://addressesapi.090227.xyz/CloudFlareYes',
    'https://addressesapi.090227.xyz/ip.164746.xyz',
    'https://ipdb.api.030101.xyz/?type=cfv4;proxy',
    'https://ipdb.api.030101.xyz/?type=bestcf&country=true',
    'https://ipdb.api.030101.xyz/?type=bestproxy&country=true',
    'https://www.wetest.vip/page/edgeone/address_v4.html',
    'https://www.wetest.vip/page/cloudfront/address_v4.html',
    'https://www.wetest.vip/page/cloudflare/address_v4.html'
]

# 免费代理池 API（返回格式：{"data":[{"ip":"x.x.x.x","port":80},...]}）
PROXY_POOL_URL = "http://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"

# >>> 4. 工具类 / 函数 <<<
class ProxyRotator:
    """简易代理池，失败即弃用"""
    def __init__(self, proxy_api: str):
        self.api = proxy_api
        self.proxies: List[str] = []
        self._fetch_proxies()

    def _fetch_proxies(self):
        try:
            data = requests.get(self.api, timeout=10).json()
            self.proxies = [f"http://{p['ip']}:{p['port']}" for p in data.get("data", [])]
            random.shuffle(self.proxies)
            logging.info("代理池刷新，可用代理数：%d", len(self.proxies))
        except Exception as e:
            logging.warning("代理池获取失败: %s", e)

    def get(self) -> str:
        if not self.proxies:
            self._fetch_proxies()
        return self.proxies.pop() if self.proxies else ""

def _random_headers() -> dict:
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    }

def _sleep():
    time.sleep(random.uniform(*RANDOM_JITTER))

def _sort_ip(ip: str):
    return tuple(map(int, ip.split(".")))

# >>> 5. 网络请求 <<<
def requests_fallback(url: str) -> str:
    """先 requests + 代理重试，不行再换 Selenium"""
    proxy_rotator = ProxyRotator(PROXY_POOL_URL)
    for attempt in range(1, RETRY_TIMES + 1):
        proxy = proxy_rotator.get()
        proxies = {"http": proxy, "https": proxy} if proxy else None
        try:
            logging.info("尝试[%d/%d] %s %s", attempt, RETRY_TIMES, url, proxy or "")
            resp = requests.get(
                url,
                headers=_random_headers(),
                proxies=proxies,
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.text
            # 遇到 CF 盾或 403/503 直接走浏览器
            if resp.status_code in (403, 503, 520, 521, 522, 525):
                raise RuntimeError("CF Shield")
        except Exception as e:
            logging.warning("requests 失败: %s", e)
        _sleep()
    # 终极方案：Undetected Chrome
    return _selenium_get(url)

def _selenium_get(url: str) -> str:
    logging.info("启用 Undetected Chrome: %s", url)
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")  # Chrome 109+ 推荐
    driver = uc.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(5)  # 过 5s 盾
        return driver.page_source
    finally:
        driver.quit()

# >>> 6. 主流程 <<<
def crawl() -> Set[str]:
    ips = set()
    for u in URLS:
        try:
            html = requests_fallback(u.strip())
            found = IP_PATTERN.findall(html)
            ips.update(found)
            logging.info("从 %s 提取到 %d 个 IP", u, len(found))
        except Exception as e:
            logging.error("最终失败 %s : %s", u, e)
        _sleep()
    return ips

def save(ips: Set[str]):
    if not ips:
        logging.warning("未采集到任何 IP")
        return
    sorted_ips = sorted(ips, key=_sort_ip)
    with open(OUTPUT_FILE, "w", encoding="utf8") as f:
        f.write("\n".join(sorted_ips) + "\n")
    logging.info("已保存 %d 条 IP 到 %s", len(sorted_ips), OUTPUT_FILE)

# >>> 7. 入口 <<<
if __name__ == "__main__":
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    ip_set = crawl()
    save(ip_set)
