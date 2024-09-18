import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:root@localhost:27017/')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'web_scraper_db')
MONGO_COLLECTION_NAME = os.getenv('MONGO_COLLECTION_NAME', 'blog_posts')

# Scraping settings
ROOT_URL = "https://nutritionfacts.org/blog/"
USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT = 10
WAIT_TIME = 0.2

# Text cleaning
REPLACEMENTS = {
    """: "'",
    """: "'",
    "'": "'",
    "'": "'",
    "…": "...",
    "—": "-",
    "\u00a0": " ",
}

EXCLUDE_STARTSWITH = [
    "Written By",
    "Image Credit",
    "In health",
    "Michael Greger",
    "-Michael Greger",
    "PS:",
    "A founding member",
    "Subscribe",
    "Catch up",
    "Charity ID",
    "We  our volunteers!",
    "Interested in learning more about",
    "Check out",
    "For more on",
]