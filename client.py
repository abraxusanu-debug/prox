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
        except Exception:
            return {}
    return {}

def save_client_cfg(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

def prompt_setup():
    print('First time setup - Admin server connection')
    server = input('Admin server URL e.g. http://65.98.5.206 : ').strip()
    token = input('User token : ').strip()
    cfg = {'server_url': server.rstrip('/'), 'token': token}
    save_client_cfg(cfg)
    return cfg

def api_get(cfg, path, params=None):
    url = f"{cfg['server_url']}{path}"
    p = {'token': cfg['token']}
    if params:
        p.update(params)
    try:
        r = requests.get(url, params=p, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        return None, f'Connection refused - check server URL and port. {e}'
    except requests.exceptions.HTTPError:
        return None, f'HTTP {r.status_code}: {r.text[:200]}'
    except Exception as e:
        return None, f'Error: {e}'

def api_post(cfg, path, data):
    url = f"{cfg['server_url']}{path}?token={cfg['token']}"
    try:
        r = requests.post(url, json=data, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        return None, f'Connection refused - check server URL and port. {e}'
    except requests.exceptions.HTTPError:
        return None, f'HTTP {r.status_code}: {r.text[:200]}'
    except Exception as e:
        return None, f'Error: {e}'

def api_delete(cfg, path):
    url = f"{cfg['server_url']}{path}?token={cfg['token']}"
    try:
        r = requests.delete(url, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        return None, f'Connection refused - check server URL and port. {e}'
    except requests.exceptions.HTTPError:
        return None, f'HTTP {r.status_code}: {r.text[:200]}'
    except Exception as e:
        return None, f'Error: {e}'

def header(title):
    print('\n' + '='*60)
    print(f' {title}')
    print('='*60)

def main_menu(cfg):
    while True:
        header('Proxy Client')
        print('1. Proxies')
        print('2. Usage')
        print('3. Proxy Auth')
        print('4. IP Authorization')
        print('5. Change Admin Auth')
        print('6. Exit')
        choice = input('Select [1-6]: ').strip()
        if choice == '1':
            proxies_menu(cfg)
        elif choice == '2':
            usage_page(cfg)
        elif choice == '3':
            proxy_auth_menu(cfg)
        elif choice == '4':
            ip_auth_menu(cfg)
        elif choice == '5':
            change_admin_auth(cfg)
        elif choice == '6':
            print('Bye')
            break
        else:
            print('Invalid choice')

def proxies_menu(cfg):
    data, err = api_get(cfg, '/api/me')
    allowed = ['static_residential']
    if not err and data.get('proxy_types'):
        allowed = data.get('proxy_types')
    labels = {
        'static_residential': 'Static Residential',
        'dedicated_isp': 'Dedicated ISP'
    }
    while True:
        header('Proxies')
        options = []
        for i, ptype in enumerate(allowed, 1):
            print(f"{i}. {labels.get(ptype, ptype)}")
            options.append(ptype)
        back_num = len(options) + 1
        print(f"{back_num}. Back")
        if 'dedicated_isp' not in allowed:
            print('\nDedicated ISP: no bandwidth allocated. Request management for more.')
        choice = input(f'Select [1-{back_num}]: ').strip()
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(options):
                view_proxies(cfg, options[n-1])
            elif n == back_num:
                return
        print('Invalid choice')

def view_proxies(cfg, ptype):
    data, err = api_get(cfg, '/api/proxies', {'type': ptype})
    if err:
        print('Error:', err)
        input('Press Enter to go back')
        return
    proxies = data.get('proxies', [])
    header(f"{data.get('proxy_type', ptype)}")
    for i, p in enumerate(proxies, 1):
        print(f"{i}. {p.get('country_code')} {p.get('city_name')}  {p.get('proxy_address')}:{p.get('port')}  ASN {p.get('asn_number')}")
    if data.get('purchase_required'):
        print('\nDedicated ISP has no bandwidth allocated. Request management for more.')
    note = data.get('note')
    if note:
        print(f"\n{note}")
    if proxies:
        c = input('\nEnter number to view/copy proxy credentials, or Enter to go back: ').strip()
        if c:
            try:
                idx = int(c) - 1
                p = proxies[idx]
                print('\nProxy details:')
                print(f"  IP:       {p.get('proxy_address')}")
                print(f"  Port:     {p.get('port')}")
                print(f"  Username: {p.get('username')}")
                print(f"  Password: {p.get('password')}")
                print(f"  Format:   {p.get('username')}:{p.get('password')}@{p.get('proxy_address')}:{p.get('port')}")
                text = f"{p.get('username')}:{p.get('password')}@{p.get('proxy_address')}:{p.get('port')}"
                try:
                    pyperclip.copy(text)
                    print('\nCopied to clipboard.')
                except Exception as ce:
                    print(f'\nClipboard copy failed: {ce}')
                    print('Copy the details above manually.')
                test = input('\nTest this proxy? [y/N]: ').strip().lower()
                if test == 'y':
                    print('Testing proxy...')
                    res, terr = api_post(cfg, '/api/test-proxy', p)
                    if terr:
                        print('Test error:', terr)
                    elif res.get('online'):
                        print(f"Proxy is online. Latency: {res.get('latency_ms')} ms. External IP: {res.get('external_ip')}")
                    else:
                        print(f"Proxy test failed: {res.get('error')}")
            except Exception as e:
                print('Error:', e)
    input('Press Enter to go back')

def usage_page(cfg):
    data, err = api_get(cfg, '/api/usage')
    if err:
        print('Error:', err)
        input('Press Enter to go back')
        return
    header('Usage')
    print(f"Total bandwidth: {data.get('total_gb')} GB")
    print(f"Used bandwidth: {data.get('used_gb')} GB")
    print(f"Remaining bandwidth: {data.get('remaining_gb')} GB")
    print(f"Requests total: {data.get('requests_total')}")
    print(f"Requests successful: {data.get('requests_successful')}")
    last = data.get('last_request_sent_at')
    if last:
        print(f"Last request: {last}")
    else:
        print("No usage recorded yet.")
    input('\nPress Enter to go back')

def proxy_auth_menu(cfg):
    while True:
        header('Proxy Auth')
        print('1. View credentials')
        print('2. Edit credentials')
        print('3. Back')
        choice = input('Select [1-3]: ').strip()
        if choice == '1':
            data, err = api_get(cfg, '/api/proxy-auth')
            if err:
                print('Error:', err)
            else:
                print(f"Username: {data.get('username')}")
                print(f"Password: {data.get('password')}")
            input('Press Enter to go back')
        elif choice == '2':
            data, err = api_get(cfg, '/api/proxy-auth')
            if err:
                print('Error:', err)
                input('Press Enter to go back')
                continue
            print(f"Current username: {data.get('username')}")
            new_user = input('New username (Enter to keep): ').strip() or data.get('username')
            print(f"Current password: {data.get('password')}")
            new_pass = input('New password (Enter to keep): ').strip() or data.get('password')
            res, err = api_post(cfg, '/api/proxy-auth', {'username': new_user, 'password': new_pass})
            if err:
                print('Error:', err)
            else:
                print('Credentials updated.')
            input('Press Enter to go back')
        elif choice == '3':
            return
        else:
            print('Invalid choice')

def ip_auth_menu(cfg):
    while True:
        header('IP Authorization')
        print('1. List authorized IPs')
        print('2. Add IP')
        print('3. Remove IP')
        print('4. Back')
        choice = input('Select [1-4]: ').strip()
        if choice == '1':
            data, err = api_get(cfg, '/api/ip-authorizations')
            if err:
                print('Error:', err)
            else:
                results = data.get('results', [])
                if not results:
                    print('No IPs authorized.')
                for item in results:
                    print(f"ID {item.get('id')}: {item.get('ip_address')}  last used {item.get('last_used_at')}")
            input('Press Enter to go back')
        elif choice == '2':
            ip = input('IP address to authorize: ').strip()
            if ip:
                res, err = api_post(cfg, '/api/ip-authorizations', {'ip_address': ip})
                if err:
                    print('Error:', err)
                else:
                    print('IP authorized.')
            input('Press Enter to go back')
        elif choice == '3':
            auth_id = input('Authorization ID to remove: ').strip()
            if auth_id:
                res, err = api_delete(cfg, f'/api/ip-authorizations/{auth_id}')
                if err:
                    print('Error:', err)
                else:
                    print('Removed.')
            input('Press Enter to go back')
        elif choice == '4':
            return
        else:
            print('Invalid choice')

def change_admin_auth(cfg):
    header('Change Admin Auth')
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
        main_menu(cfg)
    except KeyboardInterrupt:
        print('\nExiting')
