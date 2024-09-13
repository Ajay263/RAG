**Blog Outline for Code Walkthrough**

---

### **Introduction**
In this blog post, I’ll walk you through a Python script designed to extract, clean, and process blog content from the NutritionFacts.org blog. This script uses web scraping techniques with libraries such as requests and BeautifulSoup, processes the extracted data, and organizes the content in a structured way. Web scraping is often employed to gather content at scale, and this project tackles various challenges, including filtering unwanted links, handling strange characters, and efficiently storing the results in both text and JSON formats.

The key objective of this project is to use the scraped and processed blog data to build a Retrieval-Augmented Generation (RAG) application. RAG is a cutting-edge technique that combines information retrieval (searching for relevant documents) with language generation models to create systems that can respond to questions based on a specific knowledge base. By organizing and structuring the blog content, we will be able to use it as a knowledge source that can feed into a language model, enabling it to answer health-related queries based on the NutritionFacts.org blog.

This project fits into a broader data engineering workflow, where structured blog data is not only used for analytics, but also to train machine learning models or create content summaries. The decisions made throughout this code reflect a focus on scalability, cleanliness, and resilience in the face of common web scraping hurdles such as slow responses or inconsistent HTML structures.

---

### **Code Walkthrough**

**Imports**

```python
import pandas as pd  
import time  
# Makes HTTP requests to fetch web content.
import requests 
# Parses HTML for easy extraction of elements
from bs4 import BeautifulSoup  .
```

**Character Replacements**

```python
REPLACEMENTS: dict[str, str] = {
    "“": "'",
    "”": "'",
    "’": "'",
    "‘": "'",
    "…": "...",
    "—": "-",
    "\u00a0": " ",
}
```

- This is a  dictionary that maps various strange or non-standard characters (commonly found in web content) to more standard equivalents. For instance, converting curly quotes to straight quotes. This improves the readability of the scraped text and ensures consistency when storing or displaying data later.

**Excluded Texts**

```python
EXCLUDE_STARTSWITH: list[str] = [
    "Written By", "Image Credit", "In health", "Michael Greger", 
    "-Michael Greger", "PS:", "A founding member", 
    "Subscribe", "Catch up", "Charity ID", "We  our volunteers!", 
    "Interested in learning more about", "Check out", "For more on",
]
```

- This list contains strings that mark paragraphs or sections that should be ignored during scraping. Often, web content includes irrelevant sections like author credits, promotional content, or subscription links that aren't useful for data analysis or training.

**Fetching Web Content**

```python
def get_webpage_content(url: str, timeout: int = 10) -> requests.Response | None:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
    return response
```

- This function sends an HTTP GET request to fetch the HTML content of a webpage. It includes a timeout to avoid hanging indefinitely on slow connections.
- It also handles network issues with `try-except` to avoid crashing and ensures the function returns `None` in case of failure.
- A custom `User-Agent`  was set so that the code can  mimick a legitimate browser request and avoiding potential blocks by the server.

**Filtering Links**

```python
def filter_links(links: list[str], root: str) -> list[str]:
    filtered_links: list[str] = []
    for href in links:
        if not href.startswith(root):
            continue
        link_tail: str = href.replace(root, "")
        if link_tail and not link_tail.startswith("page"):
            filtered_links.append(href)
    return filtered_links
```

- It Filters the extracted links to ensure they belong to the same root URL, discarding links that aren’t relevant or lead to paginated content.
- Using `startswith()` is a fast string operation. This avoids unnecessary regular expressions.

**Extracting All URLs**

```python
def extract_all_urls(root: str, page_stop: int | None = None, wait: float = 0.2) -> list[str]:
    i_page: int = 0
    url_list: list[str] = []
    while True:
        time.sleep(wait)  
        i_page += 1
        if page_stop is not None and i_page > page_stop:
            break
        page_url = f"{root}page/{i_page}/" if i_page > 1 else root
        response = get_webpage_content(page_url)
        if response is None:
            break
        soup = BeautifulSoup(response.content, "html.parser")
        links = sorted({link["href"] for link in soup.find_all("a", href=True)})
        blog_posts_of_page = filter_links(links, root)
        if len(blog_posts_of_page) < 2:
            break
        url_list.extend(blog_posts_of_page)
    return url_list
```

- It Iteratively scrapes all paginated pages until it encounters no more valid blog posts.
- The `page_stop` argument allows limiting the number of pages scraped, useful for testing or managing large datasets.
- A `wait` between page requests helps prevent IP bans from scraping too aggressively.

**Replacing Characters**

```python
def replace_strange_chars(text: str) -> str:
    return text.translate(str.maketrans(REPLACEMENTS))
```

- Replaces characters in the scraped text according to the predefined `REPLACEMENTS` dictionary.

**Extracting Metadata**

```python
def get_meta_data(soup: BeautifulSoup) -> dict:
    meta_data = {
        "title": soup.find("h1", class_="entry-title").get_text(),
        "created": soup.find("time", class_="updated")["datetime"],
        "updated": soup.find_all("time")[1]["datetime"],
    }
    return meta_data
```

- Extracts key metadata like title, creation date, and update date from the blog posts.


**Extracting Paragraphs**

```python
def get_paragraphs(soup: BeautifulSoup) -> list[str]:
    paragraphs_html = soup.find_all("p", class_="p1") or soup.find_all("p")
    paragraphs_raw = [replace_strange_chars(para_html.get_text().strip()) for para_html in paragraphs_html]
    paragraphs_clean = [
        para_raw for para_raw in paragraphs_raw if para_raw and not any(para_raw.startswith(prefix) for prefix in EXCLUDE_STARTSWITH)
    ]
    return paragraphs_clean
```

- Extracts and cleans the blog's main content, removing unwanted paragraphs based on predefined exclusion criteria.
- If there are no `p1` paragraphs, it defaults to extracting all `p` tags, making the code more robust to layout changes.

**Key Takeaways**

```python
def get_key_takeaways(soup: BeautifulSoup) -> list[str]:
    key_takeaways_heading = soup.find("p", string="KEY TAKEAWAYS")
    if key_takeaways_heading is None:
        return []
    key_takeaways_list = key_takeaways_heading.find_next("ul")
    return [replace_strange_chars(li.get_text().strip()) for li in key_takeaways_list.find_all("li")]
```

- Searches for a specific "KEY TAKEAWAYS" section, then scrapes the bullet points (if any).
- The function checks for the existence of the takeaways section and gracefully handles the case where it doesn’t exist by returning an empty list.




**Extracting Blog Data**


```python
def extract_blog_data(soup: BeautifulSoup) -> dict:
    """Uses BeautifulSoup to parse the HTML and extract metadata, categories, tags, paragraphs, and key takeaways.

    Args:
        soup (BeautifulSoup): Parsed HTML of the blog page.

    Returns:
        dict: A dictionary containing the blog's metadata, paragraphs, categories, and key takeaways.
    """
    # Extract metadata
    blog_content: dict = get_meta_data(soup) 
    # Extract tags 
    tags_raw = soup.find("article").get("class")  
    blog_content["category"] = [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")]
    blog_content["blog_tags"] = [tag.split("-")[1:] for tag in tags_raw if tag.startswith("tag-")]
    blog_content["raw_tags"] = tags_raw

    # Extract paragraphs
    blog_content["paragraphs"] = get_paragraphs(soup)  
    #  Extract key takeaway
    blog_content["key_takeaways"] = get_key_takeaways(soup)  

    return blog_content
```


**Setting up Paths and Directories**

```python
import json
import time
from pathlib import Path

# Define and create necessary directories
data_path = Path(".").resolve() / "data"
blog_posts_root: Path = data_path / "blog_posts"
post_path_raw: Path = blog_posts_root / "raw_txt"
post_path_json: Path = blog_posts_root / "json"

data_path.mkdir(parents=True, exist_ok=True)
blog_posts_root.mkdir(parents=True, exist_ok=True)
post_path_raw.mkdir(parents=True, exist_ok=True)
post_path_json.mkdir(parents=True, exist_ok=True)

# Confirm directory creation
print(data_path.is_dir())  
print(post_path_raw.is_dir())
print(post_path_json.is_dir())
```
- Set up paths for storing raw text and JSON files and ensure the directories exist.

**Fetch and Process URLs**

```python
root_url: str = "https://nutritionfacts.org/blog/"
file_url_list: Path = blog_posts_root / "blog_posts_urls.csv"

# Get webpage content
response = get_webpage_content(root_url)  
soup = BeautifulSoup(response.content, "html.parser")

links: set[str] = sorted({link["href"] for link in soup.find_all("a", href=True)})
# Filter links
blog_posts_of_page: list[str] = filter_links(links, root_url)  
n_posts: int = len(blog_posts_of_page)
print(f"Number of blog posts: {n_posts}")

# Extract all URLs
urls_list: list[str] = extract_all_urls(root=root_url, page_stop=None)  
```

This part Extracts URLs from the blog page, filters them, and prepares them for processing.

**Extract Blog Content and Metadata**

```python
# Read URLs from CSV file
with open(blog_posts_root / file_url_list) as f:
    urls_list: list[str] = f.read().splitlines()

# Example for testing
blog_post_url = urls_list[1111]
url_tail = blog_post_url.replace(root_url, "").replace("/", "")
response = get_webpage_content(blog_post_url)
soup = BeautifulSoup(response.content, "html.parser")

# Write raw HTML to file
with open(f"{url_tail}.html", "w") as f:
    f.write(str(soup))

# Extract and save clean paragraphs
paragraphs_raw = soup.find_all("p", class_="p1")
content = "\n\n".join(para.get_text() for para in paragraphs_raw)
with open(f"{url_tail}.txt", "w") as f:
    f.write(content)

# Extract and save metadata
meta_data = get_meta_data(soup)
title_text = soup.find("h1", class_="entry-title").get_text()
date_created = soup.find("time", class_="updated")["datetime"]
date_last_update = soup.find_all("time")[1]["datetime"]
print("Datetime 01:", date_created)
print("Datetime 02:", date_last_update)

# Clean and extract paragraphs
paragraphs_html = soup.find_all("p", class_="p1") or soup.find_all("p")
paragraphs_raw = [para.get_text().strip() for para in paragraphs_html]
exclude_startswith = [...]
paragraphs_clean = [replace_strange_chars(para_raw) for para_raw in paragraphs_raw if para_raw and not any(para_raw.startswith(prefix) for prefix in exclude_startswith)]

# Extract key takeaways
key_takeaways_heading = soup.find("p", string="KEY TAKEAWAYS")
if key_takeaways_heading:
    key_takeaways_list = key_takeaways_heading.find_next("ul")
    key_takeaways = [replace_strange_chars(li.get_text().strip()) for li in key_takeaways_list.find_all("li")]

# Extract and save tags
tags_raw = soup.find("article").get("class")
tags_blog = [tag.split("-")[1] for tag in tags_raw if tag.startswith("tag-")]
cats = [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")]
```
- Extract and clean the blog content, metadata, key takeaways, and tags, saving them into appropriate files.

**Export Data to JSON**

```python
blog_data = extract_blog_data(soup)

with open(f"{url_tail}.json", "w", encoding="utf-8") as json_file:
    json.dump(blog_data, json_file, ensure_ascii=True, indent=4)
```
- Export the extracted blog data to JSON format for structured storage and further analysis.

**Real Extraction Loop**

**Pure Text Processing**
```python
for url in tqdm(urls_list):
    url_tail = url.replace(root_url, "").replace("/", "")
    file_out = post_path_raw / f"{url_tail}.txt"
    if file_out.exists():
        continue

    time.sleep(0.5)
    response = get_webpage_content(url)
    soup = BeautifulSoup(response.content, "html.parser")
    paragraphs = soup.find_all("p")
    content = "\n\n".join(para.get_text() for para in paragraphs)
    with open(file_out, "w", encoding="utf-8") as f:
        f.write(content)
```

**Metadata and JSON Processing:**
```python
for url in tqdm(urls_list):
    url_tail = url.replace(root_url, "").replace("/", "")
    file_out = post_path_json / f"{url_tail}.json"
    if file_out.exists():
        continue

    time.sleep(0.1)
    response = get_webpage_content(url)
    soup = BeautifulSoup(response.content, "html.parser")
    blog_data: dict = {"url": url}
    blog_data.update(extract_blog_data(soup))

    with open(file_out, "w", encoding="utf-8") as json_file:
        json.dump(blog_data, json_file, ensure_ascii=True, indent=4)
```

- This loop processes each URL to extract text and metadata, saving the results in both text and JSON formats.

---

