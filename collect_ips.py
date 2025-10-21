#!/usr/bin/env python3
"""
一键可用 / GitHub Actions 实测通过
依赖：
    pip install -U requests beautifulsoup4 fake-useragent undetected-chromedriver
"""

import os
import re
import time
import random
import logging
import zipfile
import stat
from typing import Set

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import undetected_chromedriver as uc

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

# ---------- 全局常量 ----------
IP_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
OUTPUT_FILE = "ip.txt"
RETRY_TIMES = 3
TIMEOUT = 8
RANDOM_JITTER = (1, 3)

URLS = [
    'https://ip.164746.xyz', 
    'https://cf.090227.xyz/CloudFlareYes', 
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

# ---------- 工具 ----------
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

# ---------- 修正版驱动下载 ----------
def get_chrome_major_version() -> str:
    raw = os.popen("google-chrome --version").read().strip()
    return raw.split()[2].split(".")[0]

def download_driver(version: str) -> str:
    zip_path = "/tmp/chromedriver.zip"
    extract_dir = "/tmp/chromedriver"
    # 先清空旧文件
    os.makedirs(extract_dir, exist_ok=True)
    for f in os.listdir(extract_dir):
        os.remove(os.path.join(extract_dir, f))

    # 1. 获取精确版本号
    api = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{version}"
    exact_version = requests.get(api, timeout=10).text.strip()
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{exact_version}/linux64/chromedriver-linux64.zip"

    logging.info("下载 chromedriver %s -> %s", exact_version, download_url)
    with requests.get(download_url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # 2. 解压
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # 3. 递归找到真正的 chromedriver 可执行文件
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file == "chromedriver":
                exec_path = os.path.join(root, file)
                os.chmod(exec_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                return exec_path

    raise FileNotFoundError("chromedriver 未在解压包内找到")

# ---------- 网络请求 ----------
# ---------- 修正后的 _selenium_get ----------
def _selenium_get(url: str) -> str:
    logging.info("启用 Undetected Chrome: %s", url)
    chrome_major = get_chrome_major_version()
    driver_path = download_driver(chrome_major)

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")

    # 关键：禁止 uc 自动下载，强制使用我们下载的 140 驱动
    driver = uc.Chrome(
        executable_path=driver_path,        # 旧接口仍可用
        version_main=int(chrome_major),     # 锁住大版本
        options=options
    )
    try:
        driver.get(url)
        time.sleep(5)
        return driver.page_source
    finally:
        driver.quit()

def requests_fallback(url: str) -> str:
    for attempt in range(1, RETRY_TIMES + 1):
        try:
            logging.info("尝试[%d/%d] %s", attempt, RETRY_TIMES, url)
            resp = requests.get(url, headers=_random_headers(), timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (403, 503, 520, 521, 522, 525):
                raise RuntimeError("CF Shield")
        except Exception as e:
            logging.warning("requests 失败: %s", e)
        _sleep()
    return _selenium_get(url)

# ---------- 主流程 ----------
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

# ---------- 入口 ----------
if __name__ == "__main__":
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    ip_set = crawl()
    save(ip_set)
