from typing import Dict, List
from config import REPLACEMENTS, EXCLUDE_STARTSWITH

def replace_strange_chars(text: str) -> str:
    """Replaces strange characters in a string with more standard equivalents."""
    return text.translate(str.maketrans(REPLACEMENTS))

def filter_paragraphs(paragraphs: List[str]) -> List[str]:
    """Filters out paragraphs that start with excluded phrases."""
    return [
        para for para in paragraphs
        if para and not any(para.startswith(prefix) for prefix in EXCLUDE_STARTSWITH)
    ]

def extract_category_and_tags(tags_raw: List[str]) -> Dict[str, List[str]]:
    """Extracts categories and tags from raw tags."""
    return {
        "category": [cat.split("-")[1] for cat in tags_raw if cat.startswith("category-")],
        "blog_tags": [tag.split("-")[1:] for tag in tags_raw if tag.startswith("tag-")],
        "raw_tags": tags_raw
    }