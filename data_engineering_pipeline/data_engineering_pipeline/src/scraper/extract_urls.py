import time
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
import requests
from config import ROOT_URL, USER_AGENT, REQUEST_TIMEOUT, WAIT_TIME

def get_webpage_content(url: str) -> Optional[requests.Response]:
    """Fetches the HTML content of a webpage."""
    logging.debug(f"Fetching URL: {url}")
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logging.info(f"Successfully fetched URL: {url}")
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None

def filter_links(links: List[str], root: str) -> List[str]:
    """Filters links by ensuring they start with the root URL and are not pagination links."""
    logging.debug(f"Filtering {len(links)} links")
    filtered_links = [
        href for href in links
        if href.startswith(root) and not href.replace(root, "").startswith("page")
    ]
    logging.info(f"Filtered down to {len(filtered_links)} links")
    return filtered_links

def extract_all_urls(root: str = ROOT_URL, page_stop: Optional[int] = None) -> List[str]:
    """Extracts all blog post URLs from paginated web pages."""
    i_page = 0
    url_list = []
    while True:
        time.sleep(WAIT_TIME)
        i_page += 1

        if page_stop is not None and i_page > page_stop:
            logging.info(f"Stopping extraction at page {i_page}")
            break

        page_url = f"{root}page/{i_page}/" if i_page > 1 else root
        logging.debug(f"Page URL: {page_url}")

        response = get_webpage_content(page_url)
        if response is None:
            break

        soup = BeautifulSoup(response.content, "html.parser")
        links = sorted({link["href"] for link in soup.find_all("a", href=True)})

        blog_posts_of_page = filter_links(links, root)
        n_posts = len(blog_posts_of_page)
        logging.info(f"Page {i_page}: Number of blog posts: {n_posts}")

        if n_posts < 2:
            logging.info(f"Not enough blog posts on page {i_page}, stopping.")
            break
        url_list.extend(blog_posts_of_page)

    logging.info(f"Extracted {len(url_list)} URLs")
    return list(set(url_list))  # Remove duplicates

def clean_urls(urls: List[str]) -> List[str]:
    """Removes URLs that are not blog posts."""
    cleaned_urls = [
        url for url in urls
        if not url.replace(ROOT_URL, "").replace("/", "").isdigit()
    ]
    logging.info(f"Number of unique blog posts after cleanup: {len(cleaned_urls)}")
    return cleaned_urls