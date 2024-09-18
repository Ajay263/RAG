from bs4 import BeautifulSoup
from typing import Any, Dict, Optional, List
import logging
from src.utils.helpers import replace_strange_chars, filter_paragraphs, extract_category_and_tags
from src.scraper.extract_urls import get_webpage_content

def get_meta_data(soup: BeautifulSoup) -> Dict[str, str]:
    """Extracts metadata from a blog page such as title, created date, and updated date."""
    logging.debug("Extracting metadata")
    return {
        "title": soup.find("h1", class_="entry-title").get_text(),
        "created": soup.find("time", class_="updated")["datetime"],
        "updated": soup.find_all("time")[1]["datetime"],
    }

def get_paragraphs(soup: BeautifulSoup) -> List[str]:
    """Extracts and cleans paragraphs from the blog content, excluding certain phrases."""
    logging.debug("Extracting paragraphs")
    paragraphs_html = soup.find_all("p", class_="p1") or soup.find_all("p")
    paragraphs_raw = [replace_strange_chars(para_html.get_text().strip()) for para_html in paragraphs_html]
    paragraphs_clean = filter_paragraphs(paragraphs_raw)
    logging.info(f"Extracted {len(paragraphs_clean)} clean paragraphs")
    return paragraphs_clean

def get_key_takeaways(soup: BeautifulSoup) -> List[str]:
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

def extract_blog_data(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Extracts all relevant blog data, including metadata, paragraphs, categories, and key takeaways."""
    logging.debug("Extracting blog data")
    blog_content = get_meta_data(soup)
    blog_content.update(extract_category_and_tags(soup.find("article").get("class")))
    blog_content["paragraphs"] = get_paragraphs(soup)
    blog_content["key_takeaways"] = get_key_takeaways(soup)
    blog_content["url"] = url
    logging.info(f"Extracted blog content with title: {blog_content.get('title')}")
    return blog_content

def scrape_blog_post(url: str) -> Optional[Dict[str, Any]]:
    """Scrapes a single blog post and returns its content."""
    response = get_webpage_content(url)
    if response is None:
        logging.warning(f"Failed to fetch URL: {url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    return extract_blog_data(soup, url)