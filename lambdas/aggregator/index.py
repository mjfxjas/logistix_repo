from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
import urllib.request
import urllib.error
from botocore.exceptions import ClientError

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    s3 = session.client('s3')
    ssm = session.client('ssm')
    
    raw_table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])
    briefs_table = dynamodb.Table(os.environ['BRIEFS_TABLE'])
    data_bucket = os.environ['DATA_BUCKET']
    today = datetime.utcnow().strftime('%Y-%m-%d')
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Fetch raw data for existing and new modules
    fuel = get_module_data(raw_table, today, 'fuel')
    freight = get_module_data(raw_table, today, 'freight')
    traffic = get_module_data(raw_table, today, 'traffic')
    weather = get_module_data(raw_table, today, 'weather')
    
    border_wait_times = get_module_data(raw_table, today, 'border-wait-times')
    economic_data = get_module_data(raw_table, today, 'economic-data')
    air_traffic = get_module_data(raw_table, today, 'air-traffic')
    ais_data = get_module_data(raw_table, today, 'ais-data')
    global_events = get_module_data(raw_table, today, 'global-events')

    # Get yesterday's data for changes
    fuel_prev = get_module_data(raw_table, yesterday, 'fuel')
    freight_prev = get_module_data(raw_table, yesterday, 'freight')
    
    # Compute changes
    fuel_data = {
        'national_avg': fuel.get('national_avg', 0),
        'national_change': calc_change(fuel.get('national_avg'), fuel_prev.get('national_avg')),
        'diesel': fuel.get('diesel', 0),
        'diesel_change': calc_change(fuel.get('diesel'), fuel_prev.get('diesel')),
        'news': fuel.get('news', [])
    }
    
    freight_data = {
        'dry_van': freight.get('dry_van', 0),
        'dry_van_change': calc_change(freight.get('dry_van'), freight_prev.get('dry_van')),
        'reefer': freight.get('reefer', 0),
        'reefer_change': calc_change(freight.get('reefer'), freight_prev.get('reefer')),
        'flatbed': freight.get('flatbed', 0),
        'flatbed_change': calc_change(freight.get('flatbed'), freight_prev.get('flatbed')),
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
        'disruption_risk': weather.get('disruption_risk', {'level': 'LOW', 'reason': 'No data'}),
        # Add new data to the brief
        'border_wait_times': border_wait_times,
        'economic_data': economic_data,
        'air_traffic': air_traffic,
        'ais_data': ais_data,
        'global_events': global_events,
    }
    
    # Generate AI insight
    brief['ai_insight'] = generate_ai_insight(ssm, brief)
    
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

def get_module_data(raw_table: Any, date: str, module: str) -> Dict[str, Any] | list:
    """
    Fetches data for a specific module and date from the raw_data table.
    Returns a dict or a list, with a sensible empty default.
    """
    # New modules are list-based, original ones are dict-based.
    is_list_based = module in [
        'border-wait-times', 'economic-data', 'air-traffic', 
        'ais-data', 'global-events', 'alerts', 'forecasts'
    ]
    default_return = [] if is_list_based else {}

    try:
        response = raw_table.get_item(Key={'date': date, 'module': module})
        item = response.get('Item')

        if not item or 'data' not in item:
            print(f"No data found for {module} on {date}")
            return default_return

        data = item['data']
        
        # Handles legacy data that was stored as a JSON string
        if isinstance(data, str):
            return json.loads(data)
        
        # If data is present but empty (e.g., empty list from ingestor), return that.
        # If it's None or something else, return the safe default.
        return data if data is not None else default_return
        
    except (ClientError, json.JSONDecodeError) as e:
        print(f"Error fetching {module} data for {date}: {e}")
        return default_return

def calc_change(current: Optional[float], previous: Optional[float]) -> float:
    if current is None or previous is None or previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 2)

def calc_fuel_score(fuel: Dict[str, Any]) -> Dict[str, str]:
    diesel_change = fuel.get('diesel_change', 0)
    if diesel_change > 2:
        return {'status': 'RISING', 'analysis': 'Prices trending up - lock in rates now'}
    elif diesel_change < -2:
        return {'status': 'FALLING', 'analysis': 'Favorable pricing window - good time to fuel'}
    else:
        return {'status': 'STABLE', 'analysis': 'Prices holding steady - no immediate action needed'}

def calc_freight_score(freight: Dict[str, Any]) -> Dict[str, str]:
    avg_change = (freight.get('dry_van_change', 0) + freight.get('reefer_change', 0) + freight.get('flatbed_change', 0)) / 3
    if avg_change > 3:
        return {'status': 'RATES UP', 'analysis': 'Strong demand - negotiate higher rates'}
    elif avg_change < -3:
        return {'status': 'RATES DOWN', 'analysis': 'Soft market - expect rate pressure'}
    else:
        return {'status': 'STEADY', 'analysis': 'Balanced market conditions'}

def calc_traffic_score(alerts: list) -> Dict[str, str]:
    count = len(alerts)
    if count >= 5:
        return {'status': 'CONGESTED', 'analysis': 'Multiple delays - add buffer time'}
    elif count >= 2:
        return {'status': 'MODERATE', 'analysis': 'Some delays expected - plan alternate routes'}
    else:
        return {'status': 'CLEAR', 'analysis': 'Smooth operations expected'}

def calc_weather_score(forecasts: list) -> Dict[str, str]:
    high_count = sum(1 for f in forecasts if f.get('severity') == 'high')
    if high_count >= 3:
        return {'status': 'SEVERE', 'analysis': 'Major disruptions likely - consider delays'}
    elif high_count >= 1:
        return {'status': 'CAUTION', 'analysis': 'Monitor conditions - prepare for impacts'}
    else:
        return {'status': 'NORMAL', 'analysis': 'Conditions favorable for operations'}

def generate_ai_insight(ssm_client: Any, brief: Dict[str, Any]) -> str:
    try:
        # Get API key from Parameter Store
        response = ssm_client.get_parameter(
            Name='/logistix/openai-api-key',
            WithDecryption=True
        )
        api_key = response['Parameter']['Value']
    except ClientError as e:
        print(f"Failed to retrieve API key: {e}")
        return f"Market conditions show diesel at ${brief.get('fuel', {}).get('diesel', 0):.2f} with freight rates averaging ${brief.get('freight', {}).get('dry_van', 0):.2f}/mile. Monitor conditions and plan accordingly."
    
    # Summarize new data for the prompt
    border_wait_times = brief.get('border_wait_times', [])
    economic_data = brief.get('economic_data', [])
    air_traffic = brief.get('air_traffic', {})
    ais_data = brief.get('ais_data', [])
    global_events = brief.get('global_events', [])
    
    border_wait_summary = f"{len(border_wait_times) if isinstance(border_wait_times, list) else 0} key ports monitored."
    economic_summary = f"{len(economic_data) if isinstance(economic_data, list) else 0} key economic indicators tracked."
    air_traffic_summary = f"{air_traffic.get('total_flights_in_bbox', 0) if isinstance(air_traffic, dict) else 0} flights tracked in US airspace."
    ais_summary = f"Sample of {len(ais_data) if isinstance(ais_data, list) else 0} maritime vessels tracked."
    events_summary = f"{len(global_events) if isinstance(global_events, list) else 0} significant global events detected."

    prompt = f"""You are a logistics operations analyst. Based on today's data, provide a 2-3 sentence insight for truck drivers and dispatchers.

Core Metrics:
- Fuel: Diesel ${brief.get('fuel', {}).get('diesel', 0):.2f} ({brief.get('fuel', {}).get('diesel_change', 0):+.1f}%)
- Freight: Dry Van ${brief.get('freight', {}).get('dry_van', 0):.2f} ({brief.get('freight', {}).get('dry_van_change', 0):+.1f}%), Reefer ${brief.get('freight', {}).get('reefer', 0):.2f} ({brief.get('freight', {}).get('reefer_change', 0):+.1f}%)
- Traffic Alerts: {len(brief.get('traffic', {}).get('alerts', []))} major incidents
- Weather: {len([w for w in brief.get('weather', {}).get('forecasts', []) if w.get('severity') == 'high'])} high-severity conditions

Extended Context:
- Border Waits: {border_wait_summary}
- Economy: {economic_summary}
- Air & Sea: {air_traffic_summary} {ais_summary}
- Global Events: {events_summary}

Highlight the most critical, cross-functional insight. What is the single most important takeaway from this combined data? Be concise and actionable."""

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
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            return result['choices'][0]['message']['content'].strip()
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"OpenAI API error: {e}")
        return f"Market conditions show diesel at ${brief.get('fuel', {}).get('diesel', 0):.2f} with freight rates averaging ${brief.get('freight', {}).get('dry_van', 0):.2f}/mile. Monitor conditions and plan accordingly."
