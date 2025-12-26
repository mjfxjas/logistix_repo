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
    economic_data = fetch_economic_indicators()
    
    table.put_item(Item={
        'date': today,
        'module': 'economic-data',
        'data': json.dumps(economic_data),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Economic data ingested')}

def fetch_economic_indicators() -> List[Dict[str, Any]]:
    # Get FRED API key from Parameter Store
    try:
        session = boto3.Session()
        ssm = session.client('ssm')
        response = ssm.get_parameter(
            Name='/logistix/fred-api-key',
            WithDecryption=True
        )
        fred_api_key = response['Parameter']['Value']
    except Exception as e:
        print(f"Failed to get FRED API key: {e}")
        fred_api_key = None
    
    # Key economic indicators for logistics
    indicators = [
        {'series': 'UNRATE', 'name': 'Unemployment Rate', 'unit': '%'},
        {'series': 'CPIAUCSL', 'name': 'Consumer Price Index', 'unit': 'Index'},
        {'series': 'DCOILWTICO', 'name': 'WTI Crude Oil', 'unit': '$/barrel'},
        {'series': 'DEXUSEU', 'name': 'USD/EUR Exchange', 'unit': 'Rate'},
        {'series': 'INDPRO', 'name': 'Industrial Production', 'unit': 'Index'}
    ]
    
    results = []
    
    if not fred_api_key:
        # Mock data when no API key
        return [
            {'name': 'Unemployment Rate', 'value': 3.7, 'unit': '%', 'change': -0.1},
            {'name': 'Consumer Price Index', 'value': 307.8, 'unit': 'Index', 'change': 0.2},
            {'name': 'WTI Crude Oil', 'value': 71.2, 'unit': '$/barrel', 'change': -1.8},
            {'name': 'USD/EUR Exchange', 'value': 1.05, 'unit': 'Rate', 'change': 0.01},
            {'name': 'Industrial Production', 'value': 103.2, 'unit': 'Index', 'change': 0.3}
        ]
    
    for indicator in indicators:
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={indicator['series']}&api_key={fred_api_key}&file_type=json&limit=2&sort_order=desc"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
                observations = data.get('observations', [])
                
                if len(observations) >= 2:
                    current = float(observations[0]['value']) if observations[0]['value'] != '.' else 0
                    previous = float(observations[1]['value']) if observations[1]['value'] != '.' else 0
                    change = round(current - previous, 2)
                    
                    results.append({
                        'name': indicator['name'],
                        'value': current,
                        'unit': indicator['unit'],
                        'change': change
                    })
        except Exception as e:
            print(f"Error fetching {indicator['name']}: {e}")
            continue
    
    return results if results else [
        {'name': 'Economic Data', 'value': 0, 'unit': 'N/A', 'change': 0}
    ]