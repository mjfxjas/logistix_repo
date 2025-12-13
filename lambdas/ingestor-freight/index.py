import json
import os
from datetime import datetime
import boto3
from news_fetcher import get_news_items

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])

# Manual freight rates - update weekly from industry reports
# Sources: DAT Trendlines, FreightWaves SONAR, Truckstop.com reports
FREIGHT_RATES = {
    'dry_van': 2.15,
    'reefer': 2.68,
    'flatbed': 2.92,
    'last_updated': '2025-12-01'
}

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    freight_data = fetch_freight_rates()
    
    table.put_item(Item={
        'date': today,
        'module': 'freight',
        'data': json.dumps(freight_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Freight data ingested')}

def fetch_freight_rates():
    result = FREIGHT_RATES.copy()
    result['news'] = get_news_items('https://www.freightwaves.com/feed', 3)
    return result
