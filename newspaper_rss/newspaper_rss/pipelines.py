import sqlite3
import os
import json

class SQLitePipeline:

    def __init__(self):
        self.file = None
        self.base_output_path = os.getenv('OUTPUT_PATH').rsplit('.', 1)[0]
        self.output_index = 1
        self.file_size_limit = 50 * 1024 * 1024  # 50 MB limit
        self.lang_file = None
        self.lang_output_path = self.base_output_path + "_lang.json"
        self.seen_combinations = set()

    def open_spider(self, spider):
        db_path = '/app/newspaper_rss/sqlite.db'
        if not os.path.exists('/app/newspaper_rss'):
            os.makedirs('/app/newspaper_rss')
        
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Newspaper(
                id INTEGER PRIMARY KEY,
                country TEXT,
                websites TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS RssLinks(
                id INTEGER PRIMARY KEY,
                links TEXT,
                lang TEXT,
                country TEXT,
                website TEXT
            )
        ''')

        self.connection.commit()

        # Initialize the JSON output files
        self.file = open(f"{self.base_output_path}_{self.output_index}.json", 'w', encoding='utf-8')
     

    def process_item(self, item, spider):
        try:
            self.connection.execute('BEGIN TRANSACTION;')
            
            if spider.name == "newspaper_spider":
                self.cursor.execute('''
                    INSERT INTO Newspaper (country, websites) VALUES(?, ?)
                ''', (item.get('country'), item.get('website')))
            
            if spider.name == "news_spider":
                item_copy = dict(item)
                if 'rss_link' in item_copy:
                    del item_copy['rss_link']
                line = json.dumps(item_copy, ensure_ascii=False) + "\n"
                self.file.write(line)
                self.file.flush()
                
                if os.stat(self.file.name).st_size > self.file_size_limit:
                    self.file.close()
                    self.output_index += 1
                    self.file = open(f"{self.base_output_path}_{self.output_index}.json", 'w', encoding='utf-8')
                
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            spider.logger.error(f"Error processing item: {e}")
        return item

    def process_rss_link(self, data,spider):
        try:
            self.cursor.execute('''
                INSERT INTO RssLinks (links, country, website) VALUES(?, ?, ?)
            ''', (data['links'], data['country'], data['website']))
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            spider.logger.error(f"Error processing RSS link: {e}")

    def update_newspaper_lang(self, rss_url, lang, spider):
        try:
            self.cursor.execute('''
                UPDATE RssLinks SET lang = ? WHERE links = ?
            ''', (lang, rss_url))
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            spider.logger.error(f"Error updating RssLinks lang: {e}")
