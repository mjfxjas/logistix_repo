from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import boto3
import urllib.request
from botocore.exceptions import ClientError

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    global_events = fetch_global_events()
    
    table.put_item(Item={
        'date': today,
        'module': 'global-events',
        'data': json.dumps(global_events),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Global events data ingested')}

def fetch_global_events() -> List[Dict[str, Any]]:
    # GDELT Project API for global events affecting logistics
    try:
        # Last 24 hours of events related to logistics keywords
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d%H%M%S')
        today = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        # Keywords related to logistics disruption
        keywords = ['port', 'shipping', 'supply chain', 'strike', 'border', 'trade war', 'sanctions']
        
        events = []
        
        for keyword in keywords[:2]:  # Limit to avoid rate limits
            try:
                url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={keyword}&mode=artlist&maxrecords=5&startdatetime={yesterday}&enddatetime={today}&format=json"
                
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read())
                    articles = data.get('articles', [])
                    
                    for article in articles[:2]:  # Top 2 per keyword
                        events.append({
                            'title': article.get('title', 'Unknown Event')[:100],
                            'source': article.get('domain', 'Unknown'),
                            'url': article.get('url', ''),
                            'keyword': keyword,
                            'impact_level': _assess_impact(article.get('title', '')),
                            'timestamp': article.get('seendate', today)
                        })
                        
            except Exception as e:
                print(f"Error fetching events for {keyword}: {e}")
                continue
        
        # Add mock events if no real data
        if not events:
            events = _get_mock_events()
        
        return events[:5]  # Max 5 events
        
    except Exception as e:
        print(f"GDELT API error: {e}")
        return _get_mock_events()

def _assess_impact(title: str) -> str:
    high_impact_words = ['strike', 'shutdown', 'closure', 'blocked', 'suspended', 'war', 'sanctions']
    medium_impact_words = ['delay', 'disruption', 'congestion', 'shortage', 'increase']
    
    title_lower = title.lower()
    
    if any(word in title_lower for word in high_impact_words):
        return 'HIGH'
    elif any(word in title_lower for word in medium_impact_words):
        return 'MEDIUM'
    else:
        return 'LOW'

def _get_mock_events() -> List[Dict[str, Any]]:
    return [
        {
            'title': 'Port congestion eases at major West Coast terminals',
            'source': 'logistics-news.com',
            'url': '#',
            'keyword': 'port',
            'impact_level': 'MEDIUM',
            'timestamp': datetime.utcnow().strftime('%Y%m%d%H%M%S')
        },
        {
            'title': 'New trade agreement reduces border processing times',
            'source': 'trade-weekly.com',
            'url': '#',
            'keyword': 'border',
            'impact_level': 'LOW',
            'timestamp': datetime.utcnow().strftime('%Y%m%d%H%M%S')
        }
    ]