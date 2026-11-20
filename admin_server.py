#!/usr/bin/env python3
import json, os
from flask import Flask, request, jsonify, abort
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
WEBSHARE_BASE = 'https://proxy.webshare.io/api/v2'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

app = Flask(__name__)

def get_user_by_token(token):
    cfg = load_config()
    for uname, u in cfg.get('users', {}).items():
        if u.get('token') == token:
            u['_username'] = uname
            return u
    return None

def webshare_headers(cfg):
    return {'Authorization': f'Token {cfg["webshare_api_key"]}'}

@app.route('/api/health')
def health():
    return jsonify({'status':'ok'})

@app.route('/api/proxies')
def api_proxies():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    try:
        params = {'mode': 'direct', 'page_size': 100}
        # Prefer static residential label for user
        # Fetch from Webshare
        r = requests.get(f'{WEBSHARE_BASE}/proxy/list/', headers=webshare_headers(cfg), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        proxies = data.get('results', [])
        # Enrich with labels for UI
        enriched = []
        for p in proxies[:10]:
            enriched.append({
                'id': p.get('id'),
                'proxy_address': p.get('proxy_address'),
                'port': p.get('port'),
                'username': p.get('username'),
                'password': p.get('password'),
                'country_code': p.get('country_code'),
                'city_name': p.get('city_name'),
                'proxy_type_label': 'Static Residential',
                'asn_number': p.get('asn_number'),
                'valid': p.get('valid')
            })
        # Add a second option category for ISP - simulated
        isp_mock = {
            'id': 'isp-demo',
            'proxy_address': '203.0.113.10',
            'port': 3128,
            'username': 'isp_user',
            'password': 'isp_pass',
            'country_code': 'US',
            'city_name': 'Los Angeles',
            'proxy_type_label': 'Dedicated ISP - Purchase Required',
            'asn_number': None,
            'valid': True
        }
        enriched.append(isp_mock)
        return jsonify({
            'mode': user.get('mode'),
            'multiplier': user.get('multiplier',1) if user.get('mode')=='simulated' else 1,
            'bandwidth_label_gb': user.get('bandwidth_label_gb',1),
            'proxies': enriched,
            'note': 'More locations are loading as your account sets up.'
        })
    except Exception as e:
        # Fallback mock list with differentiation
        mock = [
            {'id':'m1','proxy_address':'1.2.3.4','port':8080,'username':'u1','password':'p1','country_code':'US','city_name':'New York','proxy_type_label':'Static Residential','asn_number':'20738','valid':True},
            {'id':'m2','proxy_address':'5.6.7.8','port':8080,'username':'u2','password':'p2','country_code':'DE','city_name':'Berlin','proxy_type_label':'Static Residential','asn_number':'3320','valid':True},
            {'id':'m3','proxy_address':'9.10.11.12','port':8080,'username':'u3','password':'p3','country_code':'GB','city_name':'London','proxy_type_label':'Static Residential','asn_number':'20738','valid':True},
        ]
        return jsonify({'mode': user.get('mode'), 'proxies': mock, 'fallback': True, 'error': str(e)})

@app.route('/api/usage')
def api_usage():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401)
    base_bandwidth_gb = float(user.get('bandwidth_base_gb', 1.0))
    multiplier = 1
    if user.get('mode') == 'simulated':
        multiplier = user.get('multiplier', 1)
    reported_bandwidth = round(base_bandwidth_gb * multiplier, 2)
    # Mock usage metrics
    base_requests = 1234
    stats = {
        'mode': user.get('mode'),
        'multiplier': multiplier,
        'bandwidth_base_gb': base_bandwidth_gb,
        'bandwidth_reported_gb': reported_bandwidth,
        'bandwidth_label': f'{reported_bandwidth} GB',
        'requests_total': int(base_requests * multiplier),
        'requests_successful': int(base_requests * 0.97 * multiplier),
        'proxy_type': 'Static Residential',
        'isp_option_available': True
    }
    return jsonify(stats)

if __name__ == '__main__':
    # Run stable, threaded server
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
