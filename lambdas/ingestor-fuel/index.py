import json
import os
from datetime import datetime
import boto3
import urllib.request
import urllib.error
from news_fetcher import get_news_items

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])

MOCK_NEWS = [
    {'title': 'Diesel prices hold steady amid stable crude markets', 'url': 'https://www.eia.gov'},
    {'title': 'Weekly petroleum status report released', 'url': 'https://www.eia.gov'}
]

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    fuel_data = fetch_fuel_prices()
    
    table.put_item(Item={
        'date': today,
        'module': 'fuel',
        'data': json.dumps(fuel_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Fuel data ingested')}

def fetch_fuel_prices():
    api_key = os.environ.get('EIA_API_KEY')
    news = get_news_items('https://www.eia.gov/rss/petroleum.xml', 3) or MOCK_NEWS
    
    if not api_key:
        return {
            'national_avg': 3.45,
            'diesel': 4.12,
            'regions': {'northeast': 3.52, 'midwest': 3.38, 'south': 3.41, 'west': 3.58},
            'news': news
        }
    
    try:
        url = f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={api_key}&frequency=weekly&data[0]=value&facets[product][]=EPD2D&facets[product][]=EPMR&sort[0][column]=period&sort[0][direction]=desc&length=1"
        
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            prices = {}
            
            for item in data.get('response', {}).get('data', []):
                product = item.get('product-name', '')
                value = float(item.get('value', 0))
                
                if 'Diesel' in product:
                    prices['diesel'] = value
                elif 'Regular' in product:
                    prices['national_avg'] = value
            
            return {
                'national_avg': prices.get('national_avg', 3.45),
                'diesel': prices.get('diesel', 4.12),
                'regions': {'northeast': 3.52, 'midwest': 3.38, 'south': 3.41, 'west': 3.58},
                'news': news
            }
    except Exception as e:
        print(f"EIA API error: {e}")
        return {
            'national_avg': 3.45,
            'diesel': 4.12,
            'regions': {'northeast': 3.52, 'midwest': 3.38, 'south': 3.41, 'west': 3.58},
            'news': news
        }
