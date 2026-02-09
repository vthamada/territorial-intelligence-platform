from __future__ import annotations


def normalize_pagination(page: int, page_size: int, max_page_size: int = 1000) -> tuple[int, int, int]:
    clean_page = max(1, page)
    clean_page_size = max(1, min(page_size, max_page_size))
    offset = (clean_page - 1) * clean_page_size
    return clean_page, clean_page_size, offset
