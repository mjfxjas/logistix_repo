from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any
import boto3
import urllib.request
from botocore.exceptions import ClientError

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    air_traffic_data = fetch_air_traffic_data()
    
    table.put_item(Item={
        'date': today,
        'module': 'air-traffic',
        'data': json.dumps(air_traffic_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Air traffic data ingested')}

def fetch_air_traffic_data() -> Dict[str, Any]:
    # OpenSky Network API for real flight data
    try:
        # US bounding box (approximate)
        bbox = "25,-125,49,-66"  # min_lat, min_lon, max_lat, max_lon
        url = f"https://opensky-network.org/api/states/all?lamin=25&lomin=-125&lamax=49&lomax=-66"
        
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read())
            states = data.get('states', [])
            
            total_flights = len(states)
            cargo_flights = sum(1 for s in states if s[1] and ('cargo' in s[1].lower() or 'fedex' in s[1].lower() or 'ups' in s[1].lower()))
            
            # Major cargo hubs
            hubs = analyze_hub_activity(states)
            
            return {
                'total_flights_in_bbox': total_flights,
                'cargo_flights': cargo_flights,
                'major_hubs': hubs,
                'data_source': 'OpenSky Network',
                'timestamp': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        print(f"OpenSky API error: {e}")
        
        # Mock data fallback
        return {
            'total_flights_in_bbox': 4250,
            'cargo_flights': 180,
            'major_hubs': [
                {'name': 'Memphis (FDX)', 'flights': 45, 'status': 'NORMAL'},
                {'name': 'Louisville (UPS)', 'flights': 38, 'status': 'NORMAL'},
                {'name': 'Anchorage (ANC)', 'flights': 22, 'status': 'NORMAL'},
                {'name': 'Miami (MIA)', 'flights': 31, 'status': 'BUSY'}
            ],
            'data_source': 'Mock Data',
            'timestamp': datetime.utcnow().isoformat()
        }

def analyze_hub_activity(states: list) -> list:
    # Major cargo hub coordinates (approximate)
    hubs = [
        {'name': 'Memphis (FDX)', 'lat': 35.04, 'lon': -89.98, 'flights': 0},
        {'name': 'Louisville (UPS)', 'lat': 38.17, 'lon': -85.74, 'flights': 0},
        {'name': 'Anchorage (ANC)', 'lat': 61.17, 'lon': -149.99, 'flights': 0},
        {'name': 'Miami (MIA)', 'lat': 25.79, 'lon': -80.29, 'flights': 0}
    ]
    
    # Count flights near each hub (within ~50km)
    for state in states:
        if len(state) >= 7 and state[6] and state[5]:  # lat, lon exist
            lat, lon = state[6], state[5]
            
            for hub in hubs:
                # Simple distance check (rough)
                if abs(lat - hub['lat']) < 0.5 and abs(lon - hub['lon']) < 0.5:
                    hub['flights'] += 1
    
    # Add status based on activity
    for hub in hubs:
        if hub['flights'] > 40:
            hub['status'] = 'BUSY'
        elif hub['flights'] > 20:
            hub['status'] = 'NORMAL'
        else:
            hub['status'] = 'QUIET'
    
    return hubs