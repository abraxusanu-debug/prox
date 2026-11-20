#!/usr/bin/env python3
import json, os
from flask import Flask, request, jsonify, abort
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
WEBSHARE_BASE = 'https://proxy.webshare.io/api/v2'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

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

@app.route('/api/proxies')
def api_proxies():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401)
    cfg = load_config()
    try:
        # fetch proxy list from Webshare
        params = {'mode': 'direct', 'page_size': 100}
        # country filter if configured
        countries = user.get('proxy_countries')
        if countries:
            codes = [c for c in countries.keys() if c != 'ZZ']
            if codes:
                params['country_code__in'] = ','.join(codes)
        r = requests.get(f'{WEBSHARE_BASE}/proxy/list/', headers=webshare_headers(cfg), params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        proxies = data.get('results', [])
        # If ZZ, return as-is
        return jsonify({'mode': user.get('mode'), 'proxies': proxies})
    except Exception as e:
        # fallback mock
        mock = [
            {'proxy_address': '1.2.3.4', 'port': 8080, 'username': 'u1', 'password': 'p1', 'country_code': 'US', 'city_name': 'New York'},
            {'proxy_address': '5.6.7.8', 'port': 8080, 'username': 'u2', 'password': 'p2', 'country_code': 'DE', 'city_name': 'Berlin'},
        ]
        return jsonify({'mode': user.get('mode'), 'proxies': mock, 'fallback': True, 'error': str(e)})

@app.route('/api/usage')
def api_usage():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401)
    cfg = load_config()
    # In a real setup we would call Webshare stats endpoints.
    # For demo we return mock stats.
    base_stats = {
        'bandwidth_total_gb': 1.0,
        'requests_total': 1234,
        'requests_successful': 1200
    }
    multiplier = 1
    if user.get('mode') == 'simulated':
        multiplier = user.get('multiplier', 1)
    stats = {
        'mode': user.get('mode'),
        'multiplier': multiplier,
        'bandwidth_total_gb': round(base_stats['bandwidth_total_gb'] * multiplier, 2),
        'requests_total': int(base_stats['requests_total'] * multiplier),
        'requests_successful': int(base_stats['requests_successful'] * multiplier)
    }
    return jsonify(stats)

@app.route('/api/auth', methods=['POST'])
def api_auth():
    # Allow admin to update user token / mode from server side via simple header
    # For demo, just return ok
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
