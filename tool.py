import os
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional

class SecurityConferenceCrawler:
    def __init__(self, download_dir='./download'):
        self.download_dir = download_dir
        self.setup_logging()
        self.setup_directory()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.current_year = datetime.now().year

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('conference_crawler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_directory(self):
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        # Create conference-specific directories
        for conf in ['USENIX', 'SP', 'CCS', 'NDSS']:
            conf_dir = os.path.join(self.download_dir, conf)
            if not os.path.exists(conf_dir):
                os.makedirs(conf_dir)

    def verify_pdf_link(self, url: str) -> bool:
        """验证PDF链接是否有效"""
        try:
            response = self.session.head(url, timeout=10)
            content_type = response.headers.get('Content-Type', '').lower()
            return (response.status_code == 200 and 
                    ('pdf' in content_type or url.lower().endswith('.pdf')))
        except requests.exceptions.RequestException:
            return False

    def generate_conference_urls(self) -> Dict[str, List[str]]:
        """生成各会议历年的URL"""
        conference_urls = {
            'USENIX': [],
            'SP': [],
            'CCS': [],
            'NDSS': []
        }
        
        start_year = 2010
        
        # USENIX Security URLs
        for year in range(start_year, self.current_year + 1):
            conference_urls['USENIX'].append(
                f'https://www.usenix.org/conference/usenixsecurity{str(year)[-2:]}/technical-sessions'
            )
        
        # IEEE S&P URLs
        for year in range(start_year, self.current_year + 1):
            conference_urls['SP'].append(
                f'https://www.ieee-security.org/TC/SP{year}/program.html'
            )
        
        # ACM CCS URLs
        for year in range(start_year, self.current_year + 1):
            conference_urls['CCS'].append(
                f'https://www.sigsac.org/ccs/CCS{year}/accepted-papers.html'
            )
        
        # NDSS URLs
        for year in range(start_year, self.current_year + 1):
            conference_urls['NDSS'].append(
                f'https://www.ndss-symposium.org/{year}/accepted-papers/'
            )
        
        return conference_urls

    def extract_pdf_links(self, html_content: str, base_url: str) -> List[Tuple[str, str]]:
        """提取页面中的PDF链接和论文标题"""
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        # 查找所有可能的PDF链接
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if not href:
                continue
                
            # 规范化URL
            full_url = urljoin(base_url, href)
            
            # 提取论文标题
            title = link.get_text().strip()
            if not title:
                title = os.path.basename(urlparse(full_url).path)
            
            # 清理标题中的非法字符
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                pdf_links.append((full_url, title))
                
        return pdf_links

    def download_paper(self, url: str, conf_name: str, year: int, title: str) -> bool:
        """下载单篇论文"""
        try:
            # 验证链接
            if not self.verify_pdf_link(url):
                self.logger.warning(f"Invalid PDF link: {url}")
                return False
                
            # 构建保存路径
            filename = f"{year}_{title}.pdf"
            conf_dir = os.path.join(self.download_dir, conf_name)
            filepath = os.path.join(conf_dir, filename)
            
            # 检查是否已下载
            if os.path.exists(filepath):
                self.logger.info(f"File already exists: {filepath}")
                return True
                
            # 下载文件
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            self.logger.info(f"Successfully downloaded: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {str(e)}")
            return False

    def process_conference(self, conf_name: str, url: str, year: int) -> int:
        """处理单个会议页面"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            pdf_links = self.extract_pdf_links(response.text, url)
            success_count = 0
            
            for pdf_url, title in pdf_links:
                if self.download_paper(pdf_url, conf_name, year, title):
                    success_count += 1
                time.sleep(1)  # 避免请求过快
                
            return success_count
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error processing {conf_name} {year}: {str(e)}")
            return 0

    def run(self):
        """运行爬虫"""
        conference_urls = self.generate_conference_urls()
        
        for conf_name, urls in conference_urls.items():
            self.logger.info(f"\nProcessing {conf_name} conference papers...")
            
            for i, url in enumerate(urls):
                year = 2010 + i
                if year > self.current_year:
                    break
                    
                self.logger.info(f"\nProcessing {conf_name} {year}...")
                papers_count = self.process_conference(conf_name, url, year)
                self.logger.info(f"Successfully downloaded {papers_count} papers from {conf_name} {year}")
                time.sleep(2)  # 会议间隔

def main():
    crawler = SecurityConferenceCrawler()
    crawler.run()

if __name__ == "__main__":
    main()