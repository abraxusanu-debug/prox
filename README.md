# Proxy Admin + CLI Client

## Admin Server

`admin_server.py` runs a Flask API on `http://0.0.0.0:5000`.

Endpoints:

- `GET /api/proxies?token=...&type=static_residential|dedicated_isp`
  Returns the proxy list for the selected proxy type.
- `GET /api/usage?token=...`
  Returns total, used and remaining bandwidth plus request counts.
- `GET/POST /api/proxy-auth?token=...`
  View or update the proxy username/password.
- `GET/POST /api/ip-authorizations?token=...`
  List or add IP authorizations.
- `DELETE /api/ip-authorizations/<id>?token=...`
  Remove an IP authorization.

Config is `config.json`:

```json
{
  "webshare_api_key": "...",
  "users": {
    "username": {
      "token": "...",
      "proxy_countries": {"ZZ": 10},
      "total_bandwidth_gb": 15.0,
      "usage_factor": 15.0,
      "request_factor": 15.0
    }
  }
}
```

Edit `config.json` to change tokens, bandwidth totals or factors. No code changes are needed.

Run:

```bash
python3 admin_server.py
```

## Client

`client.py` is a single-file CLI client for Windows/Linux.

See [CLIENT_README.md](CLIENT_README.md) for the full client setup guide.

First run creates `~/.prox_client_config.json` with the admin server URL and token.

Main menu:

1. Proxies
2. Usage
3. Proxy Auth
4. IP Authorization
5. Change Admin Auth
6. Exit

The client never contains Webshare hostnames or the API key. It only talks to the admin server.

## Notes

- Webshare API key stays server-side only.
- Admin-only simulation factors are applied by the server; the client only shows the resulting values.
- For production, use a proper WSGI server, HTTPS, and secure token storage.
