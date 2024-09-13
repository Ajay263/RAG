

import pandas as pd

import time
import requests
from bs4 import BeautifulSoup

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

def get_webpage_content(url: str, timeout: int = 10) -> requests.Response | None:
    """Fetches the HTML content of a webpage.

    Args:
        url (str): The URL of the webpage to retrieve.
        timeout (int, optional): Timeout for the request in seconds. Defaults to 10.

    Returns:
        requests.Response | None: The response object containing the HTML content, or None if an error occurs.
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

    return response

def filter_links(links: list[str], root: str) -> list[str]:
    """Filters links by ensuring they start with the root URL and are not pagination links.

    Args:
        links (list[str]): List of extracted links from a webpage.
        root (str): The root URL to filter links that start with it.

    Returns:
        list[str]: Filtered list of links.
    """
    filtered_links: list[str] = []
    for href in links:
        if not href.startswith(root):
            continue
        link_tail: str = href.replace(root, "")
        if link_tail and not link_tail.startswith("page"):
            filtered_links.append(href)

    return filtered_links

def extract_all_urls(root: str, page_stop: int | None = None, wait: float = 0.2) -> list[str]:
    """Extracts all blog post URLs from paginated web pages.

    Args:
        root (str): The base URL of the website to scrape.
        page_stop (int | None, optional): Stop after a certain number of pages. Defaults to None (no limit).
        wait (float, optional): Delay between page requests to avoid blocking. Defaults to 0.2.

    Returns:
        list[str]: List of all blog post URLs.
    """
    i_page: int = 0
    url_list: list[str] = []
    while True:
        time.sleep(wait)  # wait a bit to avoid being blocked
        i_page += 1

        if page_stop is not None and i_page > page_stop:
            break

        if i_page == 1:
            page_url = root
        else:
            page_url = f"{root}page/{i_page}/"
        print(f"{i_page}. Page URL: {page_url}")

        response = get_webpage_content(page_url)
        if response is None:
            break

        soup = BeautifulSoup(response.content, "html.parser")
        links: list[str] = sorted({link["href"] for link in soup.find_all("a", href=True)})

        blog_posts_of_page: list[str] = filter_links(links, root)
        n_posts: int = len(blog_posts_of_page)
        print(f"\t Number of blog posts: {n_posts}")

        if n_posts < 2:
            break
        url_list.extend(blog_posts_of_page)

    return url_list

def replace_strange_chars(text: str) -> str:
    """Replaces strange characters in a string with more standard equivalents.

    Args:
        text (str): The input string.

    Returns:
        str: The cleaned string with replacements applied.
    """
    return text.translate(str.maketrans(REPLACEMENTS))

def get_meta_data(soup: BeautifulSoup) -> dict:
    """Extracts metadata from a blog page such as title, created date, and updated date.

    Args:
        soup (BeautifulSoup): Parsed HTML of the blog page.

    Returns:
        dict: A dictionary containing the blog's title, created date, and updated date.
    """
    meta_data = {
        "title": soup.find("h1", class_="entry-title").get_text(),
        "created": soup.find("time", class_="updated")["datetime"],
        "updated": soup.find_all("time")[1]["datetime"],
    }
    return meta_data

def get_paragraphs(soup: BeautifulSoup) -> list[str]:
    """Extracts and cleans paragraphs from the blog content, excluding certain phrases.

    Args:
        soup (BeautifulSoup): Parsed HTML of the blog page.

    Returns:
        list[str]: A list of cleaned paragraphs from the blog content.
    """
    paragraphs_html: list = soup.find_all("p", class_="p1")
    if not paragraphs_html:
        paragraphs_html = soup.find_all("p")

    paragraphs_raw: list[str] = [replace_strange_chars(para_html.get_text().strip()) for para_html in paragraphs_html]

    paragraphs_clean: list[str] = [
        para_raw
        for para_raw in paragraphs_raw
        if para_raw and not any(para_raw.startswith(prefix) for prefix in EXCLUDE_STARTSWITH)
    ]
    return paragraphs_clean

def get_key_takeaways(soup: BeautifulSoup) -> list[str]:
    """Extracts key takeaways from the blog content.

    Args:
        soup (BeautifulSoup): Parsed HTML of the blog page.

    Returns:
        list[str]: A list of key takeaways from the blog.
    """
    key_takeaways_heading = soup.find("p", string="KEY TAKEAWAYS")
    if key_takeaways_heading is None:
        return []

    key_takeaways_list = key_takeaways_heading.find_next("ul")
    return [replace_strange_chars(li.get_text().strip()) for li in key_takeaways_list.find_all("li")]

def extract_blog_data(soup: BeautifulSoup) -> dict:
    """Extracts all relevant blog data, including metadata, paragraphs, categories, and key takeaways.

    Args:
        soup (BeautifulSoup): Parsed HTML of the blog page.

    Returns:
        dict: A dictionary containing the blog's metadata, paragraphs, categories, and key takeaways.
    """
    blog_content: dict = get_meta_data(soup)

    tags_raw = soup.find("article").get("class")
    blog_content["category"] = [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")]
    blog_content["blog_tags"] = [tag.split("-")[1:] for tag in tags_raw if tag.startswith("tag-")]
    blog_content["raw_tags"] = tags_raw

    blog_content["paragraphs"] = get_paragraphs(soup)
    blog_content["key_takeaways"] = get_key_takeaways(soup)

    return blog_content

import json
import time
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

from pathlib import Path

# Define the paths relative to the current directory
data_path = Path(".").resolve() / "data"  # Now resolves to the current directory
blog_posts_root: Path = data_path / "blog_posts"
post_path_raw: Path = blog_posts_root / "raw_txt"
post_path_json: Path = blog_posts_root / "json"

# Create directories if they don't exist
data_path.mkdir(parents=True, exist_ok=True)
blog_posts_root.mkdir(parents=True, exist_ok=True)
post_path_raw.mkdir(parents=True, exist_ok=True)
post_path_json.mkdir(parents=True, exist_ok=True)

# Check if the directories exist
print(data_path.is_dir())  # Should print True
print(post_path_raw.is_dir())  # Should print True
print(post_path_json.is_dir())  # Should print True

root_url: str = "https://nutritionfacts.org/blog/"
file_url_list: Path = blog_posts_root / "blog_posts_urls.csv"

response = get_webpage_content(root_url)

# Parse the HTML content
soup = BeautifulSoup(response.content, "html.parser")

# Find all links on the page
links: set[str] = sorted({link["href"] for link in soup.find_all("a", href=True)})
print("Number of links:", len(links))

# filter the links
blog_posts_of_page: list[str] = filter_links(links, root_url)
n_posts: int = len(blog_posts_of_page)
print(f"Number of blog posts: {n_posts}")

"""### Extract urls of all blog posts"""

urls_list: list[str] = extract_all_urls(root=root_url, page_stop=None)

blog_post_urls_set = set(urls_list)
print("Number of unique blog posts:", len(blog_post_urls_set))
# Number of blog posts: 1290

# post processing
for url in list(blog_post_urls_set):  # create a copy of the set
    link_tail: str = url.replace(root_url, "").replace("/", "")
    # remove some urls that are not blog posts
    if link_tail.isdigit():
        print(url)
        blog_post_urls_set.remove(url)
print("Number of unique blog posts:", len(blog_post_urls_set))
# Number of unique blog posts: 1287

# export to csv file
with open(blog_posts_root / file_url_list, "w") as f:
    for url in sorted(blog_post_urls_set):
        f.write(f"{url}\n")

"""### Extract content of each blog post"""

# read from csv file
with open(blog_posts_root / file_url_list) as f:
    urls_list: list[str] = f.read().splitlines()

"""### Testing"""

blog_post_url = urls_list[1111]
url_tail = blog_post_url.replace(root_url, "").replace("/", "")
url_tail

blog_post_url

response = get_webpage_content(blog_post_url)
# Parse the HTML content
soup = BeautifulSoup(response.content, "html.parser")

# write to file
with open(f"{url_tail}.html", "w") as f:
    f.write(str(soup))

"""### pure content"""

# Extract the content you are interested in
paragraphs_raw = soup.find_all("p", class_="p1")
content = "\n\n".join(para.get_text() for para in paragraphs_raw)
paragraphs_raw

with open(f"{url_tail}.txt", "w") as f:
    f.write(content)

"""### meta data"""

meta_data = get_meta_data(soup)
meta_data

title_text = soup.find("h1", class_="entry-title").get_text()
title_text

# Extract the first datetime value
date_created = soup.find("time", class_="updated")["datetime"]

# Extract the second datetime value (using the second <time> tag)
date_last_update = soup.find_all("time")[1]["datetime"]

print("Datetime 01:", date_created)
print("Datetime 02:", date_last_update)

"""### paragraphs"""

paragraphs_clean = get_paragraphs(soup)
paragraphs_clean

paragraphs_html: list = soup.find_all("p", class_="p1")
if not paragraphs_html:
    paragraphs_html = soup.find_all("p")

paragraphs_raw: list[str] = [para.get_text() for para in paragraphs_html]
paragraphs_raw

# Extract and clean paragraphs while excluding those that start with certain phrases
paragraphs_raw: list[str] = [para_html.get_text().strip() for para_html in paragraphs_html]
exclude_startswith: list[str] = [
    "Written By",
    "Image Credit",
    "In health",
    "Michael Greger",
    "PS:",
    "A founding member",
    "Subscribe",
    "Catch up",
    "Charity ID",
    "We  our volunteers!",
    "Interested in learning more about",
    "Check out:",
]
# Create clean list
paragraphs_clean: list[str] = [
    replace_strange_chars(para_raw)
    for para_raw in paragraphs_raw
    if para_raw and not any(para_raw.startswith(prefix) for prefix in exclude_startswith)
]
paragraphs_clean

"""### Extract key takeaways"""

key_takeaways_heading = soup.find("p", string="KEY TAKEAWAYS")
if key_takeaways_heading is None:
    key_takeaways = []
else:
    # Find the next <ul> element after the "KEY TAKEAWAYS" heading
    key_takeaways_list = key_takeaways_heading.find_next("ul")

    # Extract the text from each <li> in the list
    key_takeaways = [replace_strange_chars(li.get_text().stripe()) for li in key_takeaways_list.find_all("li")]

# Print or use the extracted key takeaways
for takeaway in key_takeaways:
    print(takeaway)

"""### article tags"""

tags_raw = soup.find("article").get("class")
if tags_raw:
    tags_blog = [tag.split("-")[1] for tag in tags_raw if tag.startswith("tag-")]
    print(tags_blog)
    cats = [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")]
    print(cats)

"""### export to json"""

blog_data = extract_blog_data(soup)

# write to json file
with open(f"{url_tail}.json", "w", encoding="utf-8") as json_file:
    json.dump(blog_data, json_file, ensure_ascii=True, indent=4)




"""### meta data & text chunks (used in the end)"""

for url in tqdm(urls_list):
    url_tail = url.replace(root_url, "").replace("/", "")
    file_out = post_path_json / f"{url_tail}.json"
    if file_out.exists():
        continue

    time.sleep(0.1)  # wait a bit to avoid being blocked

    # get the HTML content
    response = get_webpage_content(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract the blog data
    blog_data: dict = {"url": url}
    blog_data.update(extract_blog_data(soup))

    # export to json file
    with open(file_out, "w", encoding="utf-8") as json_file:
        json.dump(blog_data, json_file, ensure_ascii=True, indent=4)









