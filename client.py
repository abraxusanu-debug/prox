#!/usr/bin/env python3
import os, json, sys
import requests
import pyperclip

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.prox_client_config.json')

def load_client_cfg():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_client_cfg(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

def prompt_setup():
    print('First time setup - Admin server connection')
    server = input('Admin server URL e.g. http://65.98.5.206:5000 : ').strip()
    token = input('User token : ').strip()
    cfg = {'server_url': server.rstrip('/'), 'token': token}
    save_client_cfg(cfg)
    return cfg

def api_get(cfg, path):
    url = f"{cfg['server_url']}{path}"
    params = {'token': cfg['token']}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        return None, f'Connection refused - check server URL and port. {e}'
    except requests.exceptions.HTTPError as e:
        return None, f'HTTP error {r.status_code}: {r.text[:200]}'
    except Exception as e:
        return None, f'Error: {e}'

def print_header(title):
    print('\n' + '='*50)
    print(f' {title}')
    print('='*50)

def menu_main(cfg):
    while True:
        print_header('Proxy Client')
        print('1. View Proxies')
        print('2. View Usage')
        print('3. Copy Proxy to Clipboard')
        print('4. Change Auth Details')
        print('5. Exit')
        choice = input('Select [1-5]: ').strip()
        if choice == '1':
            menu_proxies(cfg)
        elif choice == '2':
            menu_usage(cfg)
        elif choice == '3':
            menu_copy(cfg)
        elif choice == '4':
            change_auth(cfg)
        elif choice == '5':
            print('Bye')
            break
        else:
            print('Invalid choice')

def menu_proxies(cfg):
    data, err = api_get(cfg, '/api/proxies')
    if err:
        print('Error:', err)
        input('Press Enter to go back')
        return
    proxies = data.get('proxies', [])
    mode = data.get('mode')
    print_header(f'Proxies - Mode: {mode}')
    for i, p in enumerate(proxies, 1):
        print(f"{i}. [{p.get('proxy_type_label')}] {p.get('country_code')} {p.get('city_name')} - {p.get('proxy_address')}:{p.get('port')}  ASN:{p.get('asn_number')}")
    note = data.get('note')
    if note:
        print(f"\nNote: {note}")
    input('\nPress Enter to go back')

def menu_usage(cfg):
    data, err = api_get(cfg, '/api/usage')
    if err:
        print('Error:', err)
        input('Press Enter to go back')
        return
    print_header('Usage')
    print(f"Mode: {data.get('mode')}  Multiplier: {data.get('multiplier')}")
    print(f"Proxy Type: {data.get('proxy_type')}")
    print(f"Bandwidth base: {data.get('bandwidth_base_gb')} GB")
    print(f"Bandwidth reported to user: {data.get('bandwidth_reported_gb')} GB")
    print(f"Requests total: {data.get('requests_total')}")
    print(f"Requests successful: {data.get('requests_successful')}")
    if data.get('isp_option_available'):
        print("\nDedicated ISP proxies are available for purchase.")
    input('\nPress Enter to go back')

def menu_copy(cfg):
    # fetch proxies to get details
    data, err = api_get(cfg, '/api/proxies')
    if err:
        print('Error:', err)
        input('Press Enter to go back')
        return
    proxies = data.get('proxies', [])
    if not proxies:
        print('No proxies available')
        input('Press Enter to go back')
        return
    print_header('Copy Proxy')
    for i, p in enumerate(proxies, 1):
        print(f"{i}. {p.get('proxy_type_label')} {p.get('country_code')} {p.get('city_name')}")
    try:
        idx = int(input('Enter number to copy details: ')) - 1
        p = proxies[idx]
        text = f"{p.get('proxy_address')}:{p.get('port')}  user {p.get('username')} pass {p.get('password')}"
        pyperclip.copy(text)
        print('Copied to clipboard:', text)
    except Exception as e:
        print('Error:', e)
    input('Press Enter to go back')

def change_auth(cfg):
    print_header('Change Auth Details')
    server = input(f'Server URL [{cfg["server_url"]}]: ').strip() or cfg['server_url']
    token = input(f'Token [{cfg["token"][:6]}...]: ').strip() or cfg['token']
    cfg['server_url'] = server.rstrip('/')
    cfg['token'] = token
    save_client_cfg(cfg)
    print('Auth updated')
    input('Press Enter to go back')

if __name__ == '__main__':
    cfg = load_client_cfg()
    if not cfg or 'server_url' not in cfg or 'token' not in cfg:
        cfg = prompt_setup()
    try:
        menu_main(cfg)
    except KeyboardInterrupt:
        print('\nExiting')
