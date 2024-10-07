import sqlite3

def fetch_start_urls_from_rss():
    conn = sqlite3.connect('/app/newspaper_rss/sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT links, country FROM RssLinks;')
    urls = [(row[0], row[1]) for row in cursor.fetchall()]
    conn.close()
    return urls

def split_urls(urls, num_spiders):
    chunk_size = (len(urls) + num_spiders - 1) // num_spiders
    return [urls[i * chunk_size:(i + 1) * chunk_size] for i in range(num_spiders)]

def write_urls_to_files(url_chunks, prefix):
    for i, chunk in enumerate(url_chunks):
        with open(f'/app/data/rss_urls/{prefix}_urls_{i+1}.txt', 'w') as f:
            for url, country in chunk:
                f.write(f"{url} {country}\n")

if __name__ == "__main__":
    num_spiders = 10
    
    rss_urls = fetch_start_urls_from_rss()
    rss_url_chunks = split_urls(rss_urls, num_spiders)
    write_urls_to_files(rss_url_chunks, 'rss')
