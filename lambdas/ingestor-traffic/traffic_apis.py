import json
import os
import urllib.request

def fetch_sf_bay_511_alerts(api_key):
    """ Fetches traffic alerts from the 511 SF Bay API. """
    alerts = []
    try:
        url = f"http://api.511.org/traffic/events?api_key={api_key}&format=json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            events = data.get('events', [])
            for event in events[:10]:
                severity = event.get('severity', 'Unknown')
                if severity in ['Major', 'Moderate']:
                    headline = event.get('headline', 'Traffic incident')
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
        print(f"API request failed for url: {url} with error: {e}")
    return alerts

def fetch_az_511_alerts(api_key):
    """ Fetches traffic alerts from the AZ511 API. """
    alerts = []
    if not api_key:
        return alerts
    try:
        url = f"https://az511.com/api/v1/events?apiKey={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            events = data.get('results', [])
            for event in events:
                if event.get('Severity') in ['Major', 'Moderate']:
                    alerts.append({
                        'location': f"{event.get('RoadName')} - AZ",
                        'reason': event.get('Description'),
                        'severity': event.get('Severity').lower()
                    })
    except Exception as e:
        print(f"API request failed for url: {url} with error: {e}")
    return alerts

def fetch_utah_511_alerts(api_key):
    """ Fetches traffic alerts from the UDOT Traffic API. """
    alerts = []
    if not api_key:
        return alerts
    try:
        url = f"https://www.udottraffic.utah.gov/api/v2/get/alerts"
        headers = {'x-api-key': api_key}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            events = data.get('Alerts', [])
            for event in events:
                if event.get('properties', {}).get('severity') in ['Major', 'Moderate']:
                    properties = event.get('properties', {})
                    alerts.append({
                        'location': f"{properties.get('roadName')} - UT",
                        'reason': properties.get('description'),
                        'severity': properties.get('severity').lower()
                    })
    except Exception as e:
        print(f"API request failed for url: {url} with error: {e}")
    return alerts

def fetch_ny_511_alerts(api_key):
    """ Fetches traffic alerts from the 511NY API. """
    alerts = []
    if not api_key:
        return alerts
    try:
        url = f"https://511ny.org/api/getevents?key={api_key}&format=json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            for event in data:
                if event.get('Severity') in ['Major', 'Moderate']:
                    alerts.append({
                        'location': f"{event.get('RoadwayName')} - NY",
                        'reason': event.get('Description'),
                        'severity': event.get('Severity').lower()
                    })
    except Exception as e:
        print(f"API request failed for url: {url} with error: {e}")
    return alerts