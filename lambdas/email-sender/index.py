import json
import os
from datetime import datetime
import boto3

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

briefs_table = dynamodb.Table(os.environ['BRIEFS_TABLE'])
subscribers_table = dynamodb.Table(os.environ['SUBSCRIBERS_TABLE'])
sender_email = os.environ['SENDER_EMAIL']
dashboard_url = os.environ['DASHBOARD_URL']

def handler(event, context):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Get today's brief
    response = briefs_table.get_item(Key={'date': today})
    item = response.get('Item', {})
    if not item:
        return {'statusCode': 404, 'body': 'No brief found'}
    
    brief_str = item.get('brief', '{}')
    brief = json.loads(brief_str) if isinstance(brief_str, str) else brief_str
    
    if not brief:
        return {'statusCode': 404, 'body': 'No brief found'}
    
    # Get active subscribers
    subscribers = get_active_subscribers()
    
    # Send emails
    sent_count = 0
    for subscriber in subscribers:
        try:
            send_email(subscriber['email'], brief)
            sent_count += 1
        except Exception as e:
            print(f"Failed to send to {subscriber['email']}: {e}")
    
    return {'statusCode': 200, 'body': json.dumps(f'Sent {sent_count} emails')}

def get_active_subscribers():
    response = subscribers_table.scan(
        FilterExpression='attribute_exists(active) AND active = :true',
        ExpressionAttributeValues={':true': True}
    )
    return response.get('Items', [])

def send_email(to_email, brief):
    html_body = render_email_html(brief)
    
    ses.send_email(
        Source=sender_email,
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {
                'Data': f"LOGISTIX MORNING BRIEF - {brief['date']}",
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                }
            }
        }
    )

def render_email_html(brief):
    traffic_html = ''.join([
        f'<div style="background:#1a1a1a;padding:12px;margin:8px 0;border-left:3px solid #fff;">'
        f'<strong>{alert["location"]}</strong><br>'
        f'<span style="color:#aaa;">{alert["reason"]}</span></div>'
        for alert in brief.get('traffic', [])[:3]
    ]) or '<p>No major alerts</p>'
    
    weather_html = ''.join([
        f'<div style="padding:8px 0;border-bottom:1px solid #2a2a3e;">'
        f'<strong>{w["corridor"]}</strong>: {w["condition"]}</div>'
        for w in brief.get('weather', [])[:3]
    ]) or '<p>No major disruptions</p>'
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#000;color:#fff;font-family:'Courier New',Consolas,monospace;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:#000;padding:20px;text-align:center;border:2px solid #fff;border-bottom:none;">
            <h1 style="margin:0;font-size:18px;letter-spacing:0.1em;font-weight:700;">LOGISTIX MORNING BRIEF</h1>
            <p style="margin:10px 0 0;color:#999;font-size:12px;letter-spacing:0.05em;">{brief['date'].upper()}</p>
        </div>
        
        <div style="background:#000;padding:20px;border:2px solid #fff;border-top:none;">
            <div style="background:#fff;color:#000;padding:20px;margin-bottom:20px;">
                <h2 style="margin:0 0 15px;font-size:14px;letter-spacing:0.1em;font-weight:700;">AI ANALYSIS</h2>
                <p style="margin:0;line-height:1.6;font-size:13px;">{brief.get('ai_insight', '')}</p>
            </div>
            
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr>
                    <td style="padding:0;background:#000;border:2px solid #fff;">
                        <h3 style="margin:0;padding:10px;font-size:13px;letter-spacing:0.1em;font-weight:700;background:#fff;color:#000;border-bottom:2px solid #000;">FUEL PRICES</h3>
                        <div style="padding:12px;border-bottom:1px solid #333;font-size:12px;">
                            <span style="color:#999;font-size:11px;letter-spacing:0.05em;">DIESEL:</span>
                            <strong style="float:right;">${brief['fuel']['diesel']:.2f}/GAL <span style="color:{'#00ff00' if brief['fuel']['diesel_change'] < 0 else '#ff0000'};">{brief['fuel']['diesel_change']:+.1f}%</span></strong>
                        </div>
                    </td>
                </tr>
            </table>
            
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr>
                    <td style="padding:0;background:#000;border:2px solid #fff;">
                        <h3 style="margin:0;padding:10px;font-size:13px;letter-spacing:0.1em;font-weight:700;background:#fff;color:#000;border-bottom:2px solid #000;">FREIGHT RATES</h3>
                        <div style="padding:12px;border-bottom:1px solid #333;font-size:12px;">
                            <span style="color:#999;font-size:11px;letter-spacing:0.05em;">DRY VAN:</span>
                            <strong style="float:right;">${brief['freight']['dry_van']:.2f}/MI <span style="color:{'#ff0000' if brief['freight']['dry_van_change'] > 0 else '#00ff00'};">{brief['freight']['dry_van_change']:+.1f}%</span></strong>
                        </div>
                        <div style="padding:12px;font-size:12px;">
                            <span style="color:#999;font-size:11px;letter-spacing:0.05em;">REEFER:</span>
                            <strong style="float:right;">${brief['freight']['reefer']:.2f}/MI <span style="color:{'#ff0000' if brief['freight']['reefer_change'] > 0 else '#00ff00'};">{brief['freight']['reefer_change']:+.1f}%</span></strong>
                        </div>
                    </td>
                </tr>
            </table>
            
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr>
                    <td style="padding:0;background:#000;border:2px solid #fff;">
                        <h3 style="margin:0;padding:10px;font-size:13px;letter-spacing:0.1em;font-weight:700;background:#fff;color:#000;border-bottom:2px solid #000;">TRAFFIC ALERTS</h3>
                        <div style="padding:12px;">{traffic_html}</div>
                    </td>
                </tr>
            </table>
            
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr>
                    <td style="padding:0;background:#000;border:2px solid #fff;">
                        <h3 style="margin:0;padding:10px;font-size:13px;letter-spacing:0.1em;font-weight:700;background:#fff;color:#000;border-bottom:2px solid #000;">WEATHER CONDITIONS</h3>
                        <div style="padding:12px;">{weather_html}</div>
                    </td>
                </tr>
            </table>
            
            <div style="text-align:center;margin-top:20px;">
                <a href="{dashboard_url}" style="display:inline-block;background:#fff;color:#000;padding:12px 30px;text-decoration:none;font-weight:700;font-size:12px;letter-spacing:0.1em;border:2px solid #fff;">
                    VIEW FULL DASHBOARD
                </a>
            </div>
        </div>
        
        <div style="text-align:center;padding:20px;color:#666;font-size:11px;border:2px solid #333;border-top:none;background:#000;">
            <p style="letter-spacing:0.05em;">LOGISTIX MORNING BRIEF | $1/MONTH</p>
            <p><a href="#" style="color:#fff;text-decoration:underline;">UNSUBSCRIBE</a></p>
        </div>
    </div>
</body>
</html>
"""
