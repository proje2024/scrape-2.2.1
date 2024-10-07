import scrapy
import logging
from dateutil import parser as date_parser
import pytz
from datetime import datetime
from langdetect import detect, LangDetectException
import feedparser
import hashlib
from newspaper_rss.pipelines import SQLitePipeline
from newspaper_rss.items import RssFeedItem
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import time 
import langid

class NewsSpider(scrapy.Spider):
    name = "news_spider"

    def __init__(self, filename=None, spider_number=None, *args, **kwargs):
        super(NewsSpider, self).__init__(*args, **kwargs)
        self.filename = filename
        self.spider_number = spider_number
        self.pipeline = SQLitePipeline()
        self.unique_identifiers = set()
        self.pipeline.open_spider(self)
        self.start_time = time.time()
        self.logger.info(f"Spider {self.spider_number} initialized with file: {self.filename}")

    def start_requests(self):
        urls = self.read_urls_from_file(self.filename)
        for url, country in urls:
            if isinstance(url, str):
                self.logger.info(f"Spider {self.spider_number} processing URL: {url} from country: {country}")
                yield scrapy.Request(url=url, callback=self.parse, meta={'rss_url': url, 'country': country})
            else:
                self.logger.error(f"Spider {self.spider_number} encountered invalid URL format: {url}")

    def read_urls_from_file(self, filename):
        self.logger.info(f"Spider {self.spider_number} reading URLs from file: {filename}")
        with open(filename, 'r') as f:
            lines = f.readlines()
        urls = [(line.split()[0], line.split()[1]) for line in lines]
        self.logger.info(f"Spider {self.spider_number} read {len(urls)} URLs from {filename}")
        return urls

    def parse(self, response):
        rss_url = response.meta['rss_url']
        country = response.meta['country']
        self.logger.info(f"Spider {self.spider_number} parsing URL: {rss_url} from country: {country}")
        feed = feedparser.parse(response.text)
        for entry in feed.entries:
            item=self.process_entry(entry, rss_url, country)
            yield item

    def process_entry(self, entry, rss_url, country):
        try:
            created_date = date_parser.parse(entry.published) if "published" in entry else date_parser.parse(entry.pubDate)
            created_date = created_date.astimezone(pytz.utc)
        except Exception as e:
            self.logger.error(f"Spider {self.spider_number} error parsing date: {e}")
            return None

        identifier = self.generate_unique_id(f"{entry.title}-{created_date.isoformat()}")
        if identifier in self.unique_identifiers:
            self.logger.info(f"Spider {self.spider_number} found duplicate entry with ID: {identifier}")
            return None
        self.unique_identifiers.add(identifier)

        combined_text = f"{entry.title} {getattr(entry, 'summary', '')} {entry.content[0].value if 'content' in entry else ''}".strip()
        lang = "unknown"

        if combined_text:
            try:
                lang = detect(combined_text)
            except LangDetectException:
                self.logger.warning(f"Spider {self.spider_number} could not detect language using langdetect")

            if   not lang or lang == "unknown":
                lang, _ = langid.classify(combined_text)


        media_links = self.extract_media_links(entry)
   
        self.pipeline.update_newspaper_lang(rss_url, lang, self)
     
        item = RssFeedItem(
            type=self.determine_type(entry),
            source=self.extract_domain(rss_url),
            provider="rss",
            identifier=identifier,
            created_date=created_date.isoformat(),
            scraped_date=datetime.now(pytz.utc).isoformat(),
            metadata={
                "content": f"Başlık: {entry.title} \n {getattr(entry, 'summary', '')}",
                "author": getattr(entry, "author", "unknown"),
                "media_links": media_links,
                "lang": lang,
                "country": country,
            },
            rss_link=rss_url,
        )
        return item

    def extract_media_links(self, entry):
        media_links = set()
        if "media_content" in entry:
            media_links.update(media["url"] for media in entry.media_content if self.is_valid_media_url(media["url"]))
        elif not media_links and "enclosures" in entry:
            media_links.update(enclosure["href"] for enclosure in entry.enclosures if self.is_valid_media_url(enclosure["href"]))

        elif not media_links and "content_encoded" in entry:
            media_links.update(self._extract_links_from_html(entry.content_encoded))
     
        elif not media_links and "content" in entry:
            media_links.update(self._extract_links_from_html(entry.content[0].value))
        return list(media_links)

    def is_valid_media_url(self, url):
        return not any(keyword in url for keyword in ["logo", "icon", "social"])

    def _extract_links_from_html(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        return {tag["src"] for tag in soup.find_all(src=True) if tag.name != "script" and self.is_valid_media_url(tag["src"])}

    def generate_unique_id(self, identifier):
        return hashlib.sha256(identifier.encode()).hexdigest()

    def extract_domain(self, url):
        parsed_url = urlparse(url)
        return parsed_url.netloc.split('.')[-2]

    def determine_type(self, entry):
        return "forum" if "forum" in entry.link else "haberler"

    def closed(self, reason):
        end_time = time.time()
        total_time = end_time - self.start_time
        hours, remainder = divmod(total_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.logger.info(f"Spider {self.spider_number} closed. Reason: {reason}. Runtime: {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds")
