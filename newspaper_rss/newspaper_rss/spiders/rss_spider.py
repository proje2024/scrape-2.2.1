import scrapy
import time
from scrapy import signals
from newspaper_rss.pipelines import SQLitePipeline
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from feedsearch import search
import json

class RssSpider(scrapy.Spider):
    name = "rss_spider"

    def __init__(self, filename=None, *args, **kwargs):
        super(RssSpider, self).__init__(*args, **kwargs)
        self.filename = filename
        self.pipeline = SQLitePipeline()
        self.pipeline.open_spider(self)
        self.start_time = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(RssSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        self.start_time = time.time()
        self.logger.info("Spider opened: %s, processing file: %s", spider.name, self.filename)

    def start_requests(self):
        urls = self.read_urls_from_file(self.filename)
        for url, country in urls:
            if isinstance(url, str):
                self.logger.info(f"Processing URL: {url} from country: {country}")
                yield scrapy.Request(url=url, callback=self.parse, meta={'website': url, 'country': country})
            else:
                self.logger.error(f"Invalid URL format: {url}")

    def read_urls_from_file(self, filename):
        self.logger.info(f"Reading URLs from file: {filename}")
        with open(filename, 'r') as f:
            lines = f.readlines()
        urls = [(line.split()[0], line.split()[1]) for line in lines]
        self.logger.info(f"Read {len(urls)} URLs from {filename}")
        return urls

    def parse(self, response):
        website_url = response.meta['website']
        country = response.meta['country']
        rss_urls = self.find_rss_feed(website_url)
        for rss_url in rss_urls:
            self.save_to_file({"links": rss_url, "country": country, "website": website_url})

    def save_to_file(self, data):
        with open('rss.json', 'a') as f:
            json.dump(data, f)
            f.write("\n")

    def requests_retry_session(self, retries=5, backoff_factor=0.5, status_forcelist=(500, 502, 504, 429), session=None):
        session = session or requests.Session()
        retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def is_valid_feed(self, url):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = self.requests_retry_session().get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return "<rss" in response.text or "<feed" in response.text or "application/rss+xml" in response.text or "application/atom+xml" in response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"RSS check error: {e}")
            return False

    def find_rss_feed(self, url):
        all_feeds = set()

        # Find RSS feeds using the API
        all_feeds.update(self.find_rss_feed_api(url))

        # Find RSS feeds using the library
        all_feeds.update(self.find_rss_feed_lib(url))

        # Find RSS feeds by category
        categories = self.find_category_links(url)
        all_feeds.update(self.generate_rss_links(categories))

        return list(all_feeds)

    def find_rss_feed_api(self, url):
        try:
            api_endpoint = f"https://feedsearch.dev/api/v1/search?url={url}&info=true&favicon=false&opml=false&skip_crawl=false"
            response = self.requests_retry_session().get(api_endpoint)
            if response.status_code == 200:
                return [feed["url"] for feed in response.json() if self.is_valid_feed(feed["url"])]
            return []
        except Exception as e:
            self.logger.error(f"RSS feed search error: {e}")
            return []

    def find_rss_feed_lib(self, url):
        try:
            feeds = search(url, info=True)
            return [feed.url for feed in feeds if self.is_valid_feed(feed.url)]
        except Exception as e:
            self.logger.error(f"Feedsearch library error: {e}")
            return []

    def find_category_links(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        }
        try:
            response = self.requests_retry_session().get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            category_links = set()

            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(keyword in href for keyword in ['cat=', 'category/', 'categorie/', 'section/', 'magazine/', 'ad/', 'jobs/']):
                    category_links.add(href if href.startswith('http') else url.rstrip('/') + '/' + href.lstrip('/'))

            return list(category_links)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Category links search error: {e}")
            return []

    def generate_rss_links(self, categories):
        feed_urls = set()
        for category in categories:
            if "cat=" in category:
                rss_url = f"{category}&feed=rss2"
            elif any(keyword in category for keyword in ["category/", "categorie/", "section/", "magazine/", "ad/", "jobs/"]):
                rss_url = f"{category.rstrip('/')}/feed"
            else:
                continue
            if self.is_valid_feed(rss_url):
                feed_urls.add(rss_url)
        return list(feed_urls)

    def spider_closed(self, spider, reason):
        end_time = time.time()
        total_time = end_time - self.start_time
        hours, remainder = divmod(total_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.logger.info(f"Spider closed: {spider.name}. Reason: {reason}. Runtime: {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds")
        self.save_rss_to_db(spider)

    def save_rss_to_db(self, spider):
        with open('rss.json', 'r') as f:
            for line in f:
                data = json.loads(line)
                self.pipeline.process_rss_link(data, spider)
