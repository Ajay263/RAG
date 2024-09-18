import logging
from typing import List, Dict, Any
from tqdm import tqdm
from src.scraper.extract_urls import extract_all_urls, clean_urls
from src.scraper.scrape_content import scrape_blog_post
from src.db.mongo_handler import MongoHandler
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_and_save(url: str, mongo_handler: MongoHandler) -> None:
    """Scrapes a single blog post and saves it to MongoDB."""
    blog_content = scrape_blog_post(url)
    if blog_content:
        mongo_handler.save_blog_post(blog_content)

def main():
    mongo_handler = MongoHandler()
    try:
        mongo_handler.connect()

        # Extract and clean URLs
        logging.info("Extracting blog post URLs")
        urls_list: List[str] = extract_all_urls()
        clean_urls_list = clean_urls(urls_list)

        # Get existing URLs from MongoDB
        existing_urls = set(mongo_handler.get_all_urls())
        new_urls = set(clean_urls_list) - existing_urls

        logging.info(f"Found {len(new_urls)} new blog posts to scrape")

        # Scrape and save new blog posts
        for url in tqdm(new_urls, desc="Scraping blog posts"):
            scrape_and_save(url, mongo_handler)

        logging.info("Scraping and saving to MongoDB complete")

        # Test MongoDB connection and data retrieval
        mongo_handler.test_connection()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        mongo_handler.close()

if __name__ == "__main__":
    main()