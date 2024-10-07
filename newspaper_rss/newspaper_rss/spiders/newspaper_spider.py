import scrapy
import logging
import pytz
from datetime import datetime
from dotenv import load_dotenv
import os
import json
from newspaper_rss.items import NewspaperRssItem

class NewsPaperSpider(scrapy.Spider):
    name = "newspaper_spider"
    start_urls = [
        "https://www.allyoucanread.com/african-newspapers/",
        "https://www.allyoucanread.com/european-newspapers/",
        "https://www.allyoucanread.com/asian-newspapers/",
        "https://www.allyoucanread.com/north-american-newspapers/",
        "https://www.allyoucanread.com/australia-pacific-newspapers/",
        "https://www.allyoucanread.com/south-american-newspapers/"
    ]

    def __init__(self, *args, **kwargs):
        super(NewsPaperSpider, self).__init__(*args, **kwargs)
        self.start_time = datetime.now(pytz.utc)
        load_dotenv()
        self.rss_link_path = os.getenv("RSS_LINK_PATH")
        self.report_file_path = os.getenv("REPORT_FILE_PATH") 
        self.unique_identifiers = set()
        self.countries_data = {}

    def closed(self, reason):
        end_time = datetime.now(pytz.utc)
        duration = end_time - self.start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        result_data = {
            "Program runtime": f"{int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds",
        }
        
        self.logger.info(json.dumps(result_data, ensure_ascii=False, indent=4))

    def parse(self, response):
        try:
            countries = response.xpath('//div[@class="magazinecategories grid_4"]/a[@class="categorytitle"]')
            for country in countries:
                country_title = country.xpath("text()").get()
                self.countries_data[country_title] = []
                country_url = response.urljoin(country.xpath("@href").get())
                yield scrapy.Request(
                    url=country_url,
                    callback=self.parse_country,
                    meta={"country_title": country_title},
                )
        except Exception as e:
            logging.error(f"Error in parse method: {e}")

    def parse_country(self, response):
        try:
            websites = response.xpath('//a[@class="sublink"]/@href').getall()
            country = response.meta["country_title"]
            item = NewspaperRssItem()

            for website in websites:
                item['country'] = country
                item['website'] = website
                if item['country'] and item['website']:
                    yield item

        except Exception as e:
            logging.error(f"Error in parse_country method: {e}")
