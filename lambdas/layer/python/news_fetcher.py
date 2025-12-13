import feedparser
from datetime import datetime

def get_news_items(url, max_items=2):
    try:
        feed = feedparser.parse(url)
        items = []
        
        for entry in feed.entries[:max_items]:
            try:
                items.append({"title": entry.title, "url": entry.link})
            except:
                continue
        
        return items
    except:
        return []
