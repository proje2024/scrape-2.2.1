#!/bin/sh

# Run the Python script to split the URLs
python /app/split_urls_newspaper.py

# Run the Scrapy spider with the specified filename
exec "$@"
