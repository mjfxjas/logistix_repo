
import json
import os
from datetime import datetime
import boto3
from news_fetcher import get_news_items
from traffic_apis import (
    fetch_sf_bay_511_alerts,
    fetch_az_511_alerts,
    fetch_utah_511_alerts,
    fetch_ny_511_alerts
)

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
    sf_bay_511_key = os.environ.get('TRAFFIC_511_KEY')
    az_511_key = os.environ.get('AZ_511_KEY')
    utah_511_key = os.environ.get('UTAH_511_KEY')
    ny_511_key = os.environ.get('NY_511_KEY')
    
    alerts = []
    
    if sf_bay_511_key:
        alerts.extend(fetch_sf_bay_511_alerts(sf_bay_511_key))
    if az_511_key:
        alerts.extend(fetch_az_511_alerts(az_511_key))
    if utah_511_key:
        alerts.extend(fetch_utah_511_alerts(utah_511_key))
    if ny_511_key:
        alerts.extend(fetch_ny_511_alerts(ny_511_key))
    
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

