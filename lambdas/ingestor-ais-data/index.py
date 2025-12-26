from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import boto3
import urllib.request
from botocore.exceptions import ClientError

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(os.environ['RAW_DATA_TABLE'])
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    ais_data = fetch_maritime_data()
    
    table.put_item(Item={
        'date': today,
        'module': 'ais-data',
        'data': json.dumps(ais_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('AIS maritime data ingested')}

def fetch_maritime_data() -> List[Dict[str, Any]]:
    # Major US ports for cargo tracking
    ports = [
        {'name': 'Los Angeles', 'lat': 33.74, 'lon': -118.27, 'code': 'USLAX'},
        {'name': 'Long Beach', 'lat': 33.75, 'lon': -118.19, 'code': 'USLGB'},
        {'name': 'New York/New Jersey', 'lat': 40.67, 'lon': -74.04, 'code': 'USNYC'},
        {'name': 'Savannah', 'lat': 32.13, 'lon': -81.20, 'code': 'USSAV'},
        {'name': 'Seattle', 'lat': 47.60, 'lon': -122.33, 'code': 'USSEA'},
        {'name': 'Houston', 'lat': 29.73, 'lon': -95.27, 'code': 'USHOU'}
    ]
    
    try:
        # AISHub or MarineTraffic API (if available)
        # For now, using mock data with realistic patterns
        results = []
        
        for port in ports:
            vessel_count = _get_mock_vessel_count(port['name'])
            congestion = _calculate_congestion(vessel_count)
            
            results.append({
                'port_name': port['name'],
                'port_code': port['code'],
                'vessels_in_area': vessel_count,
                'cargo_vessels': int(vessel_count * 0.7),  # ~70% cargo
                'congestion_level': congestion,
                'avg_wait_time': _get_wait_time(congestion),
                'coordinates': {'lat': port['lat'], 'lon': port['lon']}
            })
        
        return results
        
    except Exception as e:
        print(f"AIS API error: {e}")
        return []

def _get_mock_vessel_count(port_name: str) -> int:
    # Realistic vessel counts based on port size
    counts = {
        'Los Angeles': 85,
        'Long Beach': 72,
        'New York/New Jersey': 68,
        'Savannah': 45,
        'Seattle': 38,
        'Houston': 52
    }
    return counts.get(port_name, 30)

def _calculate_congestion(vessel_count: int) -> str:
    if vessel_count > 70:
        return 'HIGH'
    elif vessel_count > 40:
        return 'MODERATE'
    else:
        return 'LOW'

def _get_wait_time(congestion: str) -> str:
    wait_times = {
        'HIGH': '3-5 days',
        'MODERATE': '1-2 days',
        'LOW': '< 1 day'
    }
    return wait_times.get(congestion, '1-2 days')