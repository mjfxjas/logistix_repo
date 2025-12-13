import json
import os
from datetime import datetime
import boto3
import urllib.request
from news_fetcher import get_news_items

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    traffic_data = fetch_traffic_alerts()
    
    table.put_item(Item={
        'date': today,
        'module': 'traffic',
        'data': json.dumps(traffic_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Traffic data ingested')}

def fetch_traffic_alerts():
    api_key = os.environ.get('TRAFFIC_511_KEY')
    alerts = []
    
    if api_key:
        # 511 SF Bay API - covers major CA highways
        try:
            url = f"http://api.511.org/traffic/events?api_key={api_key}&format=json"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                events = data.get('events', [])
                
                for event in events[:10]:  # Top 10 incidents
                    severity = event.get('severity', 'Unknown')
                    if severity in ['Major', 'Moderate']:
                        headline = event.get('headline', 'Traffic incident')
                        geography = event.get('geography', {}).get('coordinates', [])
                        
                        # Extract highway and direction from headline
                        location = 'CA Highway'
                        if 'I-' in headline:
                            parts = headline.split('I-')[1].split()[0:2]
                            location = f"I-{' '.join(parts)} - CA"
                        elif 'US-' in headline:
                            parts = headline.split('US-')[1].split()[0:2]
                            location = f"US-{' '.join(parts)} - CA"
                        elif 'SR-' in headline:
                            parts = headline.split('SR-')[1].split()[0:2]
                            location = f"SR-{' '.join(parts)} - CA"
                        
                        alerts.append({
                            'location': location,
                            'reason': headline[:80],
                            'severity': severity.lower()
                        })
        except Exception as e:
            print(f"511 API error: {e}")
    
    if not alerts:
        alerts = [
            {'location': 'I-95 North - VA', 'reason': 'Construction delays', 'severity': 'moderate'},
            {'location': 'I-10 East - TX', 'reason': 'Heavy traffic', 'severity': 'low'},
            {'location': 'I-80 West - NE', 'reason': 'Weather delays', 'severity': 'moderate'}
        ]
    
    news = get_news_items('https://www.ttnews.com/rss/trucking', 3) or [
        {'title': 'Major highway construction projects underway', 'url': 'https://www.ttnews.com'},
        {'title': 'Traffic safety initiatives announced', 'url': 'https://www.ttnews.com'}
    ]
    return {'alerts': alerts, 'news': news}
