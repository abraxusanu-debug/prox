#!/usr/bin/env python3
import os, json, sys
import requests
import pyperclip

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.prox_client_config.json')

def load_client_cfg():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_client_cfg(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

def prompt_setup():
    print('First time setup')
    server = input('Admin server URL e.g. http://localhost:5000 : ').strip()
    token = input('User token : ').strip()
    cfg = {'server_url': server.rstrip('/'), 'token': token}
    save_client_cfg(cfg)
    return cfg

def api_get(cfg, path):
    url = f"{cfg['server_url']}{path}"
    params = {'token': cfg['token']}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def simple_menu():
    cfg = load_client_cfg()
    if not cfg or 'server_url' not in cfg or 'token' not in cfg:
        cfg = prompt_setup()
    proxies_cache = []
    while True:
        print('\n=== Proxy Client ===')
        print('1. View Proxies')
        print('2. View Usage')
        print('3. Copy Proxy to Clipboard')
        print('4. Change Auth Details')
        print('5. Exit')
        choice = input('Select [1-5]: ').strip()
        if choice == '1':
            try:
                data = api_get(cfg, '/api/proxies')
                proxies = data.get('proxies', [])
                proxies_cache = proxies
                print(f"\nMode: {data.get('mode')}  Count: {len(proxies)}")
                for i, p in enumerate(proxies):
                    print(f"{i+1}. {p.get('proxy_address')}:{p.get('port')}  {p.get('country_code')} {p.get('city_name')}")
                    # hide credentials in list view
            except Exception as e:
                print('Error fetching proxies:', e)
        elif choice == '2':
            try:
                data = api_get(cfg, '/api/usage')
                print('\nUsage:')
                print(f" Mode: {data.get('mode')}  Multiplier: {data.get('multiplier')}")
                print(f" Bandwidth: {data.get('bandwidth_total_gb')} GB")
                print(f" Requests total: {data.get('requests_total')}")
                print(f" Requests successful: {data.get('requests_successful')}")
            except Exception as e:
                print('Error fetching usage:', e)
        elif choice == '3':
            if not proxies_cache:
                print('Fetch proxies first.')
                continue
            try:
                idx = int(input('Proxy number to copy: ')) - 1
                p = proxies_cache[idx]
                text = f"{p.get('proxy_address')}:{p.get('port')}  user {p.get('username')} pass {p.get('password')}"
                pyperclip.copy(text)
                print('Copied to clipboard')
            except Exception as e:
                print('Error:', e)
        elif choice == '4':
            server = input(f'Server URL [{cfg["server_url"]}]: ').strip() or cfg['server_url']
            token = input(f'Token [{cfg["token"][:4]}...]: ').strip() or cfg['token']
            cfg['server_url'] = server.rstrip('/')
            cfg['token'] = token
            save_client_cfg(cfg)
            print('Auth updated')
        elif choice == '5':
            print('Bye')
            break
        else:
            print('Invalid choice')

if __name__ == '__main__':
    try:
        simple_menu()
    except KeyboardInterrupt:
        print('\nExiting')
