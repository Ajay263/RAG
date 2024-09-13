import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from tqdm import tqdm
from pymongo import MongoClient
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Define constants for replacements and exclusions
REPLACEMENTS: dict[str, str] = {
    "“": "'",
    "”": "'",
    "’": "'",
    "‘": "'",
    "…": "...",
    "—": "-",
    "\u00a0": " ",
}

EXCLUDE_STARTSWITH: list[str] = [
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

# Add MongoDB connection setup
client = MongoClient('mongodb://root:root@localhost:27017/')
db = client['web_scraper_db']
collection = db['blog_posts']

def get_webpage_content(url: str, timeout: int = 10) -> requests.Response | None:
    """Fetches the HTML content of a webpage."""
    logging.debug(f"Fetching URL: {url}")
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        response.raise_for_status()
        logging.info(f"Successfully fetched URL: {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None
    return response

def filter_links(links: list[str], root: str) -> list[str]:
    """Filters links by ensuring they start with the root URL and are not pagination links."""
    logging.debug(f"Filtering {len(links)} links")
    filtered_links: list[str] = []
    for href in links:
        if not href.startswith(root):
            continue
        link_tail: str = href.replace(root, "")
        if link_tail and not link_tail.startswith("page"):
            filtered_links.append(href)
    logging.info(f"Filtered down to {len(filtered_links)} links")
    return filtered_links

def extract_all_urls(root: str, page_stop: int | None = None, wait: float = 0.2) -> list[str]:
    """Extracts all blog post URLs from paginated web pages."""
    i_page: int = 0
    url_list: list[str] = []
    while True:
        time.sleep(wait)  # wait a bit to avoid being blocked
        i_page += 1

        if page_stop is not None and i_page > page_stop:
            logging.info(f"Stopping extraction at page {i_page}")
            break

        if i_page == 1:
            page_url = root
        else:
            page_url = f"{root}page/{i_page}/"
        logging.debug(f"Page URL: {page_url}")

        response = get_webpage_content(page_url)
        if response is None:
            break

        soup = BeautifulSoup(response.content, "html.parser")
        links: list[str] = sorted({link["href"] for link in soup.find_all("a", href=True)})

        blog_posts_of_page: list[str] = filter_links(links, root)
        n_posts: int = len(blog_posts_of_page)
        logging.info(f"Page {i_page}: Number of blog posts: {n_posts}")

        if n_posts < 2:
            logging.info(f"Not enough blog posts on page {i_page}, stopping.")
            break
        url_list.extend(blog_posts_of_page)

    logging.info(f"Extracted {len(url_list)} URLs")
    return url_list

def replace_strange_chars(text: str) -> str:
    """Replaces strange characters in a string with more standard equivalents."""
    cleaned_text = text.translate(str.maketrans(REPLACEMENTS))
    return cleaned_text

def get_meta_data(soup: BeautifulSoup) -> dict:
    """Extracts metadata from a blog page such as title, created date, and updated date."""
    logging.debug("Extracting metadata")
    meta_data = {
        "title": soup.find("h1", class_="entry-title").get_text(),
        "created": soup.find("time", class_="updated")["datetime"],
        "updated": soup.find_all("time")[1]["datetime"],
    }
    return meta_data

def get_paragraphs(soup: BeautifulSoup) -> list[str]:
    """Extracts and cleans paragraphs from the blog content, excluding certain phrases."""
    logging.debug("Extracting paragraphs")
    paragraphs_html: list = soup.find_all("p", class_="p1")
    if not paragraphs_html:
        paragraphs_html = soup.find_all("p")

    paragraphs_raw: list[str] = [replace_strange_chars(para_html.get_text().strip()) for para_html in paragraphs_html]

    paragraphs_clean: list[str] = [
        para_raw
        for para_raw in paragraphs_raw
        if para_raw and not any(para_raw.startswith(prefix) for prefix in EXCLUDE_STARTSWITH)
    ]
    logging.info(f"Extracted {len(paragraphs_clean)} clean paragraphs")
    return paragraphs_clean

def get_key_takeaways(soup: BeautifulSoup) -> list[str]:
    """Extracts key takeaways from the blog content."""
    logging.debug("Extracting key takeaways")
    key_takeaways_heading = soup.find("p", string="KEY TAKEAWAYS")
    if key_takeaways_heading is None:
        logging.info("No key takeaways found")
        return []

    key_takeaways_list = key_takeaways_heading.find_next("ul")
    key_takeaways = [replace_strange_chars(li.get_text().strip()) for li in key_takeaways_list.find_all("li")]
    logging.info(f"Extracted {len(key_takeaways)} key takeaways")
    return key_takeaways

def extract_blog_data(soup: BeautifulSoup) -> dict:
    """Extracts all relevant blog data, including metadata, paragraphs, categories, and key takeaways."""
    logging.debug("Extracting blog data")
    blog_content: dict = get_meta_data(soup)

    tags_raw = soup.find("article").get("class")
    blog_content["category"] = [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")]
    blog_content["blog_tags"] = [tag.split("-")[1:] for tag in tags_raw if tag.startswith("tag-")]
    blog_content["raw_tags"] = tags_raw

    blog_content["paragraphs"] = get_paragraphs(soup)
    blog_content["key_takeaways"] = get_key_takeaways(soup)

    logging.info(f"Extracted blog content with title: {blog_content.get('title')}")
    return blog_content

def save_to_mongodb(blog_content: dict):
    """Saves the blog content to MongoDB."""
    logging.debug(f"Saving blog content to MongoDB: {blog_content['title']}")
    result = collection.insert_one(blog_content)
    logging.info(f"Inserted document with ID: {result.inserted_id}")

# Define the paths relative to the current directory
data_path = Path(".").resolve() / "data"
blog_posts_root: Path = data_path / "blog_posts"
post_path_raw: Path = blog_posts_root / "raw_txt"
post_path_json: Path = blog_posts_root / "json"

# Create directories if they don't exist
data_path.mkdir(parents=True, exist_ok=True)
blog_posts_root.mkdir(parents=True, exist_ok=True)
post_path_raw.mkdir(parents=True, exist_ok=True)
post_path_json.mkdir(parents=True, exist_ok=True)

# Check if the directories exist
logging.info(f"Data path exists: {data_path.is_dir()}")
logging.info(f"Post raw path exists: {post_path_raw.is_dir()}")
logging.info(f"Post JSON path exists: {post_path_json.is_dir()}")

root_url: str = "https://nutritionfacts.org/blog/"
file_url_list: Path = blog_posts_root / "blog_posts_urls.csv"

# Extract URLs of all blog posts
logging.info("Extracting blog post URLs")
urls_list: list[str] = extract_all_urls(root=root_url, page_stop=None)

blog_post_urls_set = set(urls_list)
logging.info(f"Number of unique blog posts: {len(blog_post_urls_set)}")

# Remove some URLs that are not blog posts
for url in list(blog_post_urls_set):  # create a copy of the set
    link_tail: str = url.replace(root_url, "").replace("/", "")
    if link_tail.isdigit():
        logging.debug(f"Removing non-blog post URL: {url}")
        blog_post_urls_set.remove(url)
logging.info(f"Number of unique blog posts after cleanup: {len(blog_post_urls_set)}")

# Export to CSV file
logging.info(f"Exporting URLs to {file_url_list}")
with open(blog_posts_root / file_url_list, "w") as f:
    for url in sorted(blog_post_urls_set):
        f.write(f"{url}\n")

# Extract content of each blog post
logging.info("Extracting blog post content")
for url in tqdm(blog_post_urls_set):
    response = get_webpage_content(url)
    if response is None:
        logging.warning(f"Failed to fetch URL: {url}")
        continue

    soup = BeautifulSoup(response.content, "html.parser")
    blog_content: dict = extract_blog_data(soup)
    blog_content['url'] = url  # Add the URL to the blog content
    
    save_to_mongodb(blog_content)

logging.info("Scraping and saving to MongoDB complete.")

def test_mongodb_connection():
    """Tests MongoDB connection and data retrieval."""
    logging.info("Testing MongoDB connection and data retrieval...")
    total_documents = collection.count_documents({})
    logging.info(f"Total documents in collection: {total_documents}")
    if total_documents > 0:
        sample_document = collection.find_one()
        logging.info("Sample document:")
        logging.info(json.dumps(sample_document, indent=2, default=str))
    else:
        logging.info("No documents found in the collection.")

# Call the test function after scraping
test_mongodb_connection()

# Close the MongoDB connection
logging.info("Closing MongoDB connection.")
client.close()
