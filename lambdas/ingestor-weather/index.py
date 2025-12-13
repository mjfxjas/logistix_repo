import json
import os
from datetime import datetime
import boto3
import urllib.request
from news_fetcher import get_news_items

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])

WEATHER_POINTS = [
    {'name': 'I-95 Northeast', 'lat': 40.7, 'lon': -74.0, 'state': 'NY'},
    {'name': 'I-95 Southeast', 'lat': 33.7, 'lon': -84.4, 'state': 'GA'},
    {'name': 'I-10 South', 'lat': 29.8, 'lon': -95.4, 'state': 'TX'},
    {'name': 'I-80 Midwest', 'lat': 41.9, 'lon': -87.6, 'state': 'IL'},
    {'name': 'I-40 Central', 'lat': 35.5, 'lon': -97.5, 'state': 'OK'},
    {'name': 'I-5 West Coast', 'lat': 34.0, 'lon': -118.2, 'state': 'CA'},
    {'name': 'I-90 Northwest', 'lat': 47.6, 'lon': -122.3, 'state': 'WA'},
    {'name': 'I-70 Mountain', 'lat': 39.7, 'lon': -104.9, 'state': 'CO'}
]

SEVERE_ALERT_TYPES = ['Winter Storm', 'Blizzard', 'Ice Storm', 'Flood', 'Flash Flood', 
                      'Tornado', 'Hurricane', 'High Wind', 'Extreme Cold', 'Heat']

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    weather_data = fetch_weather_forecasts()
    
    table.put_item(Item={
        'date': today,
        'module': 'weather',
        'data': json.dumps(weather_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Weather data ingested')}

def fetch_weather_forecasts():
    forecasts = []
    nws_alerts = fetch_nws_alerts()
    
    for point in WEATHER_POINTS:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={point['lat']}&longitude={point['lon']}&daily=weathercode,precipitation_sum,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                condition = analyze_weather(data, point, nws_alerts)
                
                if condition:
                    forecasts.append({
                        'corridor': point['name'],
                        'condition': condition['text'],
                        'severity': condition['severity']
                    })
        except Exception as e:
            print(f"Error fetching weather for {point['name']}: {e}")
    
    risk_score = calculate_disruption_risk(forecasts)
    
    # Fetch news from 4 US regional NWS offices
    regional_feeds = [
        'https://www.weather.gov/source/crh/rss/briefing.xml',  # Central
        'https://www.weather.gov/source/erh/rss/briefing.xml',  # Eastern
        'https://www.weather.gov/source/wrh/rss/briefing.xml',  # Western
        'https://www.weather.gov/source/srh/rss/briefing.xml'   # Southern
    ]
    
    news = []
    for feed in regional_feeds:
        items = get_news_items(feed, 1)
        if items:
            news.extend(items)
        if len(news) >= 3:
            break
    
    if not news:
        news = [
            {'title': 'Winter weather preparedness tips for drivers', 'url': 'https://www.weather.gov'},
            {'title': 'National weather service updates', 'url': 'https://www.weather.gov'}
        ]
    
    return {
        'forecasts': forecasts if forecasts else [{'corridor': 'All routes', 'condition': 'Clear conditions', 'severity': 'low'}],
        'disruption_risk': risk_score,
        'news': news
    }

def fetch_nws_alerts():
    try:
        url = 'https://api.weather.gov/alerts/active?status=actual'
        req = urllib.request.Request(url, headers={'User-Agent': 'LogisticsBriefing/1.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            alerts = {}
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                event = props.get('event', '')
                
                if any(severe in event for severe in SEVERE_ALERT_TYPES):
                    for area in props.get('areaDesc', '').split(';'):
                        state = area.strip().split(',')[-1].strip() if ',' in area else ''
                        if state not in alerts:
                            alerts[state] = []
                        alerts[state].append(event)
            
            return alerts
    except Exception as e:
        print(f"NWS alerts error: {e}")
        return {}

def analyze_weather(data, point, nws_alerts):
    daily = data.get('daily', {})
    codes = daily.get('weathercode', [])
    precip = daily.get('precipitation_sum', [])
    temp_max = daily.get('temperature_2m_max', [])
    temp_min = daily.get('temperature_2m_min', [])
    
    # Check NWS alerts first (highest priority)
    state_alerts = nws_alerts.get(point.get('state', ''), [])
    if state_alerts:
        alert_text = state_alerts[0]
        return {'text': alert_text, 'severity': 'high'}
    
    if not codes:
        return None
    
    # Check next 3 days
    for i in range(min(3, len(codes))):
        code = codes[i]
        rain = precip[i] if i < len(precip) else 0
        t_min = temp_min[i] if i < len(temp_min) else 50
        t_max = temp_max[i] if i < len(temp_max) else 70
        
        if code in [71, 73, 75, 77, 85, 86]:
            return {'text': 'Snow expected', 'severity': 'high'}
        
        if code in [63, 65, 67, 80, 81, 82] or rain > 0.5:
            return {'text': 'Heavy rain expected', 'severity': 'moderate'}
        
        if code >= 95:
            return {'text': 'Severe storms expected', 'severity': 'high'}
        
        if t_min < 20:
            return {'text': f'Extreme cold ({int(t_min)}°F)', 'severity': 'moderate'}
        
        if t_max > 100:
            return {'text': f'Extreme heat ({int(t_max)}°F)', 'severity': 'moderate'}
    
    return None

def calculate_disruption_risk(forecasts):
    if not forecasts:
        return {'level': 'LOW', 'reason': 'No severe conditions', 'top_conditions': []}
    
    high_count = sum(1 for f in forecasts if f.get('severity') == 'high')
    moderate_count = sum(1 for f in forecasts if f.get('severity') == 'moderate')
    
    # Get top 3 conditions
    sorted_forecasts = sorted(forecasts, key=lambda x: 0 if x.get('severity') == 'high' else 1)
    top_3 = [f"{f['condition']} ({f['corridor'].split()[0]})" for f in sorted_forecasts[:3]]
    
    if high_count >= 3:
        return {'level': 'HIGH', 'reason': f'{high_count} severe conditions', 'top_conditions': top_3}
    elif high_count >= 1:
        return {'level': 'MODERATE', 'reason': f'{high_count} severe + {moderate_count} moderate', 'top_conditions': top_3}
    elif moderate_count >= 4:
        return {'level': 'MODERATE', 'reason': f'{moderate_count} moderate conditions', 'top_conditions': top_3}
    else:
        return {'level': 'LOW', 'reason': 'Minor conditions', 'top_conditions': top_3}
