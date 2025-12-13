import json
import os
from datetime import datetime, timedelta
import boto3
import urllib.request

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

raw_table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])
briefs_table = dynamodb.Table(os.environ['BRIEFS_TABLE'])
data_bucket = os.environ['DATA_BUCKET']
openai_api_key = os.environ['OPENAI_API_KEY']

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Fetch raw data
    fuel = get_module_data(today, 'fuel')
    freight = get_module_data(today, 'freight')
    traffic = get_module_data(today, 'traffic')
    weather = get_module_data(today, 'weather')
    
    # Get yesterday's data for changes
    fuel_prev = get_module_data(yesterday, 'fuel')
    freight_prev = get_module_data(yesterday, 'freight')
    
    # Compute changes
    fuel_data = {
        'national_avg': fuel['national_avg'],
        'national_change': calc_change(fuel['national_avg'], fuel_prev.get('national_avg')),
        'diesel': fuel['diesel'],
        'diesel_change': calc_change(fuel['diesel'], fuel_prev.get('diesel')),
        'news': fuel.get('news', [])
    }
    
    freight_data = {
        'dry_van': freight['dry_van'],
        'dry_van_change': calc_change(freight['dry_van'], freight_prev.get('dry_van')),
        'reefer': freight['reefer'],
        'reefer_change': calc_change(freight['reefer'], freight_prev.get('reefer')),
        'flatbed': freight['flatbed'],
        'flatbed_change': calc_change(freight['flatbed'], freight_prev.get('flatbed')),
        'news': freight.get('news', [])
    }
    
    brief = {
        'date': today,
        'fuel': fuel_data,
        'fuel_score': calc_fuel_score(fuel_data),
        'freight': freight_data,
        'freight_score': calc_freight_score(freight_data),
        'traffic': {'alerts': traffic.get('alerts', []), 'news': traffic.get('news', [])},
        'traffic_score': calc_traffic_score(traffic.get('alerts', [])),
        'weather': {'forecasts': weather.get('forecasts', []), 'news': weather.get('news', [])},
        'weather_score': calc_weather_score(weather.get('forecasts', [])),
        'disruption_risk': weather.get('disruption_risk', {'level': 'LOW', 'reason': 'No data'})
    }
    
    # Generate AI insight
    brief['ai_insight'] = generate_ai_insight(brief)
    
    # Store in DynamoDB as JSON string
    briefs_table.put_item(Item={
        'date': today,
        'brief': json.dumps(brief),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Store in S3 for dashboard
    s3.put_object(
        Bucket=data_bucket,
        Key=f'{today}.json',
        Body=json.dumps(brief),
        ContentType='application/json'
    )
    
    return {'statusCode': 200, 'body': json.dumps('Brief aggregated')}

def get_module_data(date, module):
    try:
        response = raw_table.get_item(Key={'date': date, 'module': module})
        item = response.get('Item', {})
        data_str = item.get('data', '{}')
        return json.loads(data_str) if isinstance(data_str, str) else data_str
    except:
        return {}

def calc_change(current, previous):
    if not previous or previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 2)

def calc_fuel_score(fuel):
    diesel_change = fuel.get('diesel_change', 0)
    if diesel_change > 2:
        return {'status': 'RISING', 'analysis': 'Prices trending up - lock in rates now'}
    elif diesel_change < -2:
        return {'status': 'FALLING', 'analysis': 'Favorable pricing window - good time to fuel'}
    else:
        return {'status': 'STABLE', 'analysis': 'Prices holding steady - no immediate action needed'}

def calc_freight_score(freight):
    avg_change = (freight.get('dry_van_change', 0) + freight.get('reefer_change', 0) + freight.get('flatbed_change', 0)) / 3
    if avg_change > 3:
        return {'status': 'RATES UP', 'analysis': 'Strong demand - negotiate higher rates'}
    elif avg_change < -3:
        return {'status': 'RATES DOWN', 'analysis': 'Soft market - expect rate pressure'}
    else:
        return {'status': 'STEADY', 'analysis': 'Balanced market conditions'}

def calc_traffic_score(alerts):
    count = len(alerts)
    if count >= 5:
        return {'status': 'CONGESTED', 'analysis': 'Multiple delays - add buffer time'}
    elif count >= 2:
        return {'status': 'MODERATE', 'analysis': 'Some delays expected - plan alternate routes'}
    else:
        return {'status': 'CLEAR', 'analysis': 'Smooth operations expected'}

def calc_weather_score(forecasts):
    high_count = sum(1 for f in forecasts if f.get('severity') == 'high')
    if high_count >= 3:
        return {'status': 'SEVERE', 'analysis': 'Major disruptions likely - consider delays'}
    elif high_count >= 1:
        return {'status': 'CAUTION', 'analysis': 'Monitor conditions - prepare for impacts'}
    else:
        return {'status': 'NORMAL', 'analysis': 'Conditions favorable for operations'}

def generate_ai_insight(brief):
    traffic_alerts = brief['traffic'].get('alerts', []) if isinstance(brief['traffic'], dict) else brief['traffic']
    weather_forecasts = brief['weather'].get('forecasts', []) if isinstance(brief['weather'], dict) else brief['weather']
    
    prompt = f"""You are a logistics operations analyst. Based on today's data, provide a 2-3 sentence insight for truck drivers and dispatchers.

Fuel: Diesel ${brief['fuel']['diesel']:.2f} ({brief['fuel']['diesel_change']:+.1f}%)
Freight: Dry Van ${brief['freight']['dry_van']:.2f} ({brief['freight']['dry_van_change']:+.1f}%), Reefer ${brief['freight']['reefer']:.2f} ({brief['freight']['reefer_change']:+.1f}%)
Traffic Alerts: {len(traffic_alerts)} major incidents
Weather: {len([w for w in weather_forecasts if w.get('severity') == 'high'])} high-severity conditions

Highlight notable changes, suggest considerations, and mention any cautions."""

    try:
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps({
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 150,
                'temperature': 0.7
            }).encode(),
            headers={
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Market conditions show diesel at ${brief['fuel']['diesel']:.2f} with freight rates averaging ${brief['freight']['dry_van']:.2f}/mile. Monitor conditions and plan accordingly."
