# NEWSPAPER_RSS

Sırasıyla aşağıdaki docker compose dosyaları çalıştırılmalıdır.

1- docker-compose-newspaper.yml

Bu docker compose dosyası ülkelerin haber sitelerini scrape edip urllerini ve ait olduğu country değerlerini Newspaper tablosuna insert eder.

2- docker-compose-rss.yml

Bu docker compose dosyası veritabanındaki web site linklerini alır ve rss feed linklerini oluşturu ve RssLinks tablosuna rss feed linki, country ve lang değerlerini insert eder. Burda lang null basılmaktadır.

3- docker-compose-news.yml

Bu docker compose dosyası veritabanındaki rss linklerin alır ve scrape ederek data/output/output.json a basar ve lang değerlerini RssLinks tablosundaki ilgili kayıtlara ekler.

> newspaper_spider tek container olarak çalışmaktadır. rss_spider ve news_spider 10 farklı container'da çalışmaktadır. Sayısını artırmak isterseniz split_urlnewspaper.py ve split_urls_rss.py dosyalarındaki num_spiders değişkeninin değerini artırabilirsiniz. Değeri değiştirdikten sonra ilgili container'dan container sayısını güncellemeyi unutmayınız.
