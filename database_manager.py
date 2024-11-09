# database_manager.py
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Database connection settings; load these from environment variables or config file
        self.connection = psycopg2.connect(
            dbname="linkedin_scraper",
            user="postgres",
            password=os.getenv('DB_PASSWORD'),
            host="localhost",
            port="5432"
        )
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

    def insert_post(self, post_data):
        """Insert a single LinkedIn post into the database."""
        insert_query = """
        INSERT INTO linkedin_posts (profile_url, content, date, media_type, likes, comments)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        self.cursor.execute(insert_query, (
            post_data['profile_url'],
            post_data['content'],
            post_data['date'],
            post_data['media_type'],
            post_data['likes'],
            post_data['comments']
        ))

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self.connection.close()
