#!/usr/bin/env python3
import json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def ws_headers(api_key):
    return {'Authorization': f'Token {api_key}'}

def ws_get_with_key(api_key, path, params=None):
    r = requests.get(f'{WEBSHARE_BASE}{path}', headers=ws_headers(api_key), params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def ws_get_all_keys(cfg, path, params=None):
    """Fetch from all configured API keys and combine results"""
    api_keys = cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')])
    if not api_keys:
        return {'results': []}
    all_results = []
    for key in api_keys:
        try:
            data = ws_get_with_key(key, path, params)
            results = data.get('results', [])
            all_results.extend(results)
        except Exception as e:
            print(f"Error fetching from key {key[:10]}...: {e}")
            continue
    return {'results': all_results}

def ws_get(cfg, path, params=None):
    """Fetch from first API key (for stats, config, etc.)"""
    api_keys = cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')])
    if not api_keys:
        return {}
    return ws_get_with_key(api_keys[0], path, params)

def ws_patch(cfg, path, data):
    # Use first key for writes
    api_key = cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')])[0]
    r = requests.patch(f'{WEBSHARE_BASE}{path}', headers=ws_headers(api_key), json=data, timeout=15)
    r.raise_for_status()
    return r.json()

def ws_post(cfg, path, data):
    # Use first key for writes
    api_key = cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')])[0]
    r = requests.post(f'{WEBSHARE_BASE}{path}', headers=ws_headers(api_key), json=data, timeout=15)
    r.raise_for_status()
    return r.json()

def ws_delete(cfg, path):
    # Use first key for writes
    api_key = cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')])[0]
    r = requests.delete(f'{WEBSHARE_BASE}{path}', headers=ws_headers(api_key), timeout=15)
    r.raise_for_status()
    return r.json() if r.text else {'ok': True}

def test_proxy_latency(proxy_address, port, username, password, timeout=5):
    """Test proxy latency, returns (latency_ms, status) where status is 'good', 'bad', 'unreachable'"""
    if username:
        proxy_url = f'http://{username}:{password}@{proxy_address}:{port}'
    else:
        proxy_url = f'http://{proxy_address}:{port}'
    proxies = {'http': proxy_url, 'https': proxy_url}
    start = time.time()
    try:
        r = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=timeout)
        elapsed = round((time.time() - start) * 1000, 2)
        r.raise_for_status()
        if elapsed < 1000:
            return elapsed, 'good'
        elif elapsed < 3000:
            return elapsed, 'bad'
        else:
            return elapsed, 'unreachable'
    except Exception:
        return None, 'unreachable'

def test_proxies_batch(proxies, max_workers=10):
    """Test latency for multiple proxies in parallel"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {
            executor.submit(test_proxy_latency, p.get('proxy_address'), p.get('port'), 
                          p.get('username'), p.get('password')): p.get('id') 
            for p in proxies
        }
        for future in as_completed(future_to_proxy):
            proxy_id = future_to_proxy[future]
            try:
                latency, status = future.result()
                results[proxy_id] = {'latency_ms': latency, 'status': status}
            except Exception:
                results[proxy_id] = {'latency_ms': None, 'status': 'unreachable'}
    return results

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/me')
def api_me():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    return jsonify({
        'label': user.get('label'),
        'proxy_types': user.get('proxy_types', ['static_residential'])
    })

@app.route('/api/proxies')
def api_proxies():
    token = request.args.get('token')
    ptype = request.args.get('type', 'static_residential')
    test_latency = request.args.get('test_latency', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    if ptype == 'dedicated_isp':
        return jsonify({
            'proxy_type': 'Dedicated ISP',
            'proxies': [],
            'purchase_required': True,
            'note': 'Dedicated ISP has no bandwidth allocated on this account. Request management for more.',
            'page': page,
            'per_page': per_page,
            'total': 0,
            'total_pages': 0
        })
    # Static residential - real Webshare proxies from all keys
    try:
        # Fetch all proxies from both keys
        all_proxies = []
        for key in cfg.get('webshare_api_keys', [cfg.get('webshare_api_key')]):
            try:
                page_num = 1
                while True:
                    data = ws_get_with_key(key, '/proxy/list/', {'mode': 'direct', 'page_size': 100, 'page': page_num})
                    results = data.get('results', [])
                    if not results:
                        break
                    all_proxies.extend(results)
                    if not data.get('next'):
                        break
                    page_num += 1
            except Exception as e:
                print(f"Error fetching from key {key[:10]}...: {e}")
                continue
        
        # Filter only active proxies
        active_proxies = [p for p in all_proxies if p.get('valid')]
        
        # Pagination
        total = len(active_proxies)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        page_proxies = active_proxies[start:end]
        
        enriched = []
        for p in page_proxies:
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
        # Test latency if requested
        if test_latency and enriched:
            latency_results = test_proxies_batch(enriched)
            for p in enriched:
                lr = latency_results.get(p.get('id'))
                if lr:
                    p['latency_ms'] = lr['latency_ms']
                    p['latency_status'] = lr['status']
        
        return jsonify({
            'proxy_type': 'Static Residential', 
            'proxies': enriched, 
            'purchase_required': False, 
            'note': 'More locations are loading as your account sets up.',
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages
        })
    except Exception as e:
        mock = [
            {'id':'m1','proxy_address':'1.2.3.4','port':8080,'username':'u1','password':'p1','country_code':'US','city_name':'New York','proxy_type_label':'Static Residential','asn_number':'20738','valid':True},
            {'id':'m2','proxy_address':'5.6.7.8','port':8080,'username':'u2','password':'p2','country_code':'DE','city_name':'Berlin','proxy_type_label':'Static Residential','asn_number':'3320','valid':True},
        ]
        return jsonify({'proxy_type': 'Static Residential', 'proxies': mock, 'fallback': True, 'error': str(e), 'page': 1, 'per_page': per_page, 'total': 2, 'total_pages': 1})

@app.route('/api/proxy-auth', methods=['GET', 'POST'])
def api_proxy_auth():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    if request.method == 'GET':
        try:
            conf = ws_get(cfg, '/proxy/config/')
            return jsonify({'username': conf.get('username'), 'password': conf.get('password')})
        except Exception as e:
            return jsonify({'username': user.get('proxy_username', 'user'), 'password': user.get('proxy_password', 'pass'), 'error': str(e)})
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    try:
        conf = ws_patch(cfg, '/proxy/config/', {'username': username, 'password': password})
        return jsonify({'username': conf.get('username'), 'password': conf.get('password'), 'updated': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ip-authorizations', methods=['GET', 'POST'])
def api_ip_authorizations():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    if request.method == 'GET':
        try:
            data = ws_get(cfg, '/proxy/ipauthorization/')
            return jsonify(data)
        except Exception as e:
            return jsonify({'count': 0, 'results': [], 'error': str(e)})
    data = request.get_json() or {}
    ip = data.get('ip_address')
    if not ip:
        return jsonify({'error': 'ip_address required'}), 400
    try:
        res = ws_post(cfg, '/proxy/ipauthorization/', {'ip_address': ip})
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ip-authorizations/<int:auth_id>', methods=['DELETE'])
def api_delete_ip_authorization(auth_id):
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    try:
        ws_delete(cfg, f'/proxy/ipauthorization/{auth_id}/')
        return jsonify({'deleted': True, 'id': auth_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/test-proxy', methods=['POST'])
def api_test_proxy():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    data = request.get_json() or {}
    address = data.get('proxy_address')
    port = data.get('port')
    username = data.get('username')
    password = data.get('password')
    if not address or not port:
        return jsonify({'online': False, 'error': 'proxy_address and port required'}), 400
    latency, status = test_proxy_latency(address, port, username, password, timeout=10)
    if latency:
        return jsonify({'online': True, 'latency_ms': latency, 'status': status})
    else:
        return jsonify({'online': False, 'status': 'unreachable', 'error': 'Proxy not reachable'})

@app.route('/api/proxy-latency', methods=['POST'])
def api_proxy_latency():
    """Test latency for multiple proxies"""
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    data = request.get_json() or {}
    proxy_ids = data.get('proxy_ids', [])
    if not proxy_ids:
        return jsonify({'error': 'proxy_ids required'}), 400
    # Fetch all proxies first
    cfg = load_config()
    try:
        all_data = ws_get_all_keys(cfg, '/proxy/list/', {'mode': 'direct', 'page_size': 100})
        all_proxies = {p.get('id'): p for p in all_data.get('results', [])}
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    # Filter to requested IDs
    proxies_to_test = [all_proxies[pid] for pid in proxy_ids if pid in all_proxies]
    if not proxies_to_test:
        return jsonify({'results': {}})
    latency_results = test_proxies_batch(proxies_to_test)
    return jsonify({'results': latency_results})

@app.route('/api/usage')
def api_usage():
    token = request.args.get('token')
    user = get_user_by_token(token)
    if not user:
        abort(401, description='Invalid token')
    cfg = load_config()
    try:
        stats = ws_get(cfg, '/stats/aggregate/')
    except Exception:
        stats = {}
    real_bw = stats.get('bandwidth_total', 0) or 0
    real_requests = stats.get('requests_total', 0) or 0
    real_success = stats.get('requests_successful', 0) or 0
    # bandwidth_total is bytes; convert to GB
    real_gb = real_bw / (1024 ** 3) if real_bw else 0.0
    usage_factor = float(user.get('usage_factor', 1.0))
    total_gb = float(user.get('total_bandwidth_gb', 15.0))
    bandwidth_offset_gb = float(user.get('bandwidth_offset_gb', 0.0))
    used_gb = round(max(0.0, real_gb * usage_factor - bandwidth_offset_gb), 2)
    remaining_gb = round(max(0.0, total_gb - used_gb), 2)
    req_factor = float(user.get('request_factor', 1.0))
    return jsonify({
        'total_gb': total_gb,
        'used_gb': used_gb,
        'remaining_gb': remaining_gb,
        'requests_total': int(real_requests * req_factor),
        'requests_successful': int(real_success * req_factor),
        'last_request_sent_at': stats.get('last_request_sent_at')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
