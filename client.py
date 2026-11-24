#!/usr/bin/env python3
import os, json, sys
import requests
import pyperclip

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.prox_client_config.json')

# ANSI color codes
GREEN = '\033[92m'
ORANGE = '\033[33m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def colorize_latency(latency_ms, status):
    """Return color-coded latency string"""
    if latency_ms is None:
        return f"{RED}unreachable{RESET}"
    if status == 'good':
        return f"{GREEN}{latency_ms} ms{RESET}"
    elif status == 'bad':
        return f"{ORANGE}{latency_ms} ms{RESET}"
    else:
        return f"{RED}{latency_ms} ms{RESET}"

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
    page = 1
    while True:
        data, err = api_get(cfg, '/api/proxies', {'type': ptype, 'test_latency': 'false', 'page': page, 'per_page': 20})
        if err:
            print('Error:', err)
            input('Press Enter to go back')
            return
        proxies = data.get('proxies', [])
        total = data.get('total', 0)
        total_pages = data.get('total_pages', 1)
        page = data.get('page', 1)
        
        header(f"{data.get('proxy_type', ptype)} - Page {page}/{total_pages} (Total: {total} active proxies)")
        for i, p in enumerate(proxies, 1):
            latency_str = ""
            if p.get('latency_ms') is not None:
                latency_str = f"  Latency: {colorize_latency(p.get('latency_ms'), p.get('latency_status', 'unreachable'))}"
            elif p.get('latency_status'):
                latency_str = f"  Latency: {colorize_latency(None, p.get('latency_status'))}"
            print(f"{i}. {p.get('country_code')} {p.get('city_name')}  {p.get('proxy_address')}:{p.get('port')}  ASN {p.get('asn_number')}{latency_str}")
        if data.get('purchase_required'):
            print('\nDedicated ISP has no bandwidth allocated. Request management for more.')
        note = data.get('note')
        if note:
            print(f"\n{note}")
        
        # Pagination controls
        nav_options = []
        if page > 1:
            nav_options.append('[p] Previous page')
        if page < total_pages:
            nav_options.append('[n] Next page')
        nav_options.append('[number] View/copy proxy credentials')
        nav_options.append('[t] Test latency for all proxies on this page')
        nav_options.append('[Enter] Back to main menu')
        
        print('\nOptions:')
        for opt in nav_options:
            print(f'  {opt}')
        
        c = input('Select: ').strip().lower()
        
        if c == 'p' and page > 1:
            page -= 1
            continue
        elif c == 'n' and page < total_pages:
            page += 1
            continue
        elif c == 't':
            print('\nTesting latency for all proxies on this page...')
            test_all_proxies_latency(cfg, proxies)
            # Re-fetch with latency
            data2, err2 = api_get(cfg, '/api/proxies', {'type': ptype, 'test_latency': 'true', 'page': page, 'per_page': 20})
            if not err2:
                proxies = data2.get('proxies', [])
                header(f"{data2.get('proxy_type', ptype)} - Page {page}/{total_pages} (with latency)")
                for i, p in enumerate(proxies, 1):
                    latency_str = ""
                    if p.get('latency_ms') is not None:
                        latency_str = f"  Latency: {colorize_latency(p.get('latency_ms'), p.get('latency_status', 'unreachable'))}"
                    elif p.get('latency_status'):
                        latency_str = f"  Latency: {colorize_latency(None, p.get('latency_status'))}"
                    print(f"{i}. {p.get('country_code')} {p.get('city_name')}  {p.get('proxy_address')}:{p.get('port')}  ASN {p.get('asn_number')}{latency_str}")
            c = input('\nEnter number to view/copy proxy credentials, or Enter to go back: ').strip()
        if c and c not in ('p', 'n', 't'):
            try:
                idx = int(c) - 1
                if 0 <= idx < len(proxies):
                    p = proxies[idx]
                    print('\nProxy details:')
                    print(f"  IP:       {p.get('proxy_address')}")
                    print(f"  Port:     {p.get('port')}")
                    print(f"  Username: {p.get('username')}")
                    print(f"  Password: {p.get('password')}")
                    print(f"  Format:   {p.get('username')}:{p.get('password')}@{p.get('proxy_address')}:{p.get('port')}")
                    latency_str = ""
                    if p.get('latency_ms') is not None:
                        latency_str = f"  Latency: {colorize_latency(p.get('latency_ms'), p.get('latency_status', 'unreachable'))}"
                    elif p.get('latency_status'):
                        latency_str = f"  Latency: {colorize_latency(None, p.get('latency_status'))}"
                    if latency_str:
                        print(latency_str)
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
                            print(f"Proxy is online. Latency: {colorize_latency(res.get('latency_ms'), res.get('status', 'unreachable'))}. External IP: {res.get('external_ip')}")
                        else:
                            print(f"Proxy test failed: {res.get('error')}")
                else:
                    print('Invalid proxy number')
            except Exception as e:
                print('Error:', e)
            input('\nPress Enter to continue...')
    input('Press Enter to go back')

def test_all_proxies_latency(cfg, proxies):
    """Test latency for all proxies via batch endpoint"""
    proxy_ids = [p.get('id') for p in proxies if p.get('id')]
    if not proxy_ids:
        print('No proxies to test')
        return
    res, err = api_post(cfg, '/api/proxy-latency', {'proxy_ids': proxy_ids})
    if err:
        print(f'Latency test error: {err}')
    else:
        print(f'Tested {len(res.get("results", {}))} proxies')

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
