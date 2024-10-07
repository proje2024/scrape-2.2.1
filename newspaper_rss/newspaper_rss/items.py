import scrapy

class NewspaperRssItem(scrapy.Item):
    country = scrapy.Field()
    website = scrapy.Field()
    links = scrapy.Field()
    lang = scrapy.Field()

class RssFeedItem(scrapy.Item):
    type = scrapy.Field()
    source = scrapy.Field()
    provider = scrapy.Field()
    identifier = scrapy.Field()
    created_date = scrapy.Field()
    scraped_date = scrapy.Field()
    metadata = scrapy.Field()
    rss_link = scrapy.Field()

