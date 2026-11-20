# Proxy Admin + CLI Client

## Admin Server
`admin_server.py` runs a Flask API on http://0.0.0.0:5000

Endpoints:
- GET /api/proxies?token=...
  Returns proxy list from Webshare for the user. Admin can set proxy_countries per user.
- GET /api/usage?token=...
  Returns usage stats. If user mode is simulated, values are multiplied by `multiplier`.

Config is `config.json`:
{
  "webshare_api_key": "...",
  "users": {
    "username": {
      "token": "...",
      "mode": "simulated|real",
      "multiplier": 15,
      "proxy_countries": {"ZZ":10}
    }
  }
}

Edit config.json to change mode / multiplier / token. No code changes needed.

Run:
python3 admin_server.py

## Client
`client.py` is a single-file CLI client for Windows/Linux.

First run creates ~/.prox_client_config.json with server URL and token.

Menu:
1. View Proxies - fetches from admin server
2. View Usage - shows multiplied stats for simulated users
3. Copy Proxy to Clipboard - copies host:port user pass
4. Change Auth Details - updates server URL / token
5. Exit

The client never contains Webshare hostnames or API key. It only talks to your admin server.

## Notes
- Webshare API key stays server-side only.
- Simulated mode is admin-visible only; user sees multiplied numbers.
- For production, use a proper WSGI server, HTTPS, and secure token storage.
