from __future__ import annotations

import feedparser
from datetime import datetime
from typing import List, Dict, Any

def get_news_items(url: str, max_items: int = 2) -> List[Dict[str, str]]:
    try:
        feed = feedparser.parse(url)
        items = []
        
        for entry in feed.entries[:max_items]:
            try:
                items.append({"title": entry.title, "url": entry.link})
            except (AttributeError, KeyError):
                continue
        
        return items
    except Exception as e:
        print(f"Feed parsing error for {url}: {e}")
        return []
