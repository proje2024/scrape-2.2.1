#!/bin/sh

# Run the Python script to split the URLs
python /app/split_urls_rss.py

# Run the Scrapy spider with the specified filename
exec "$@"
