# Proxy Client – Setup Guide

This guide is for users running the single-file CLI client on Windows or Linux.

## Requirements

- Python 3.8+
- Internet access to the admin server
- Clipboard support (optional, for the copy feature)

Install dependencies:

```bash
pip install requests pyperclip
```

On Linux, clipboard copy may also need `xclip` or `xsel`:

```bash
sudo apt install xclip
```

## Download

Download `client.py` from the repository. It is a single file and does not need any other project files.

## First run

```bash
python3 client.py
```

On Windows:

```powershell
python client.py
```

The first run asks for:

- **Admin server URL** – e.g. `http://65.98.5.206:5000`
- **User token** – provided by the admin

These are saved to `~/.prox_client_config.json` so you only enter them once.

## Main menu

```
1. Proxies
2. Usage
3. Proxy Auth
4. IP Authorization
5. Change Admin Auth
6. Exit
```

### Proxies

Choose:
1. **Static Residential** – shows the residential proxies assigned to your account.
2. **Dedicated ISP** – shows dedicated ISP options. Some entries may be marked as purchase-required.
3. **Back**

Each row shows country, city, host:port and ASN. After the list you can enter a proxy number to copy its credentials, or press Enter to go back. At the end of the list the client shows:

> More locations are loading as your account sets up.

### Usage

Shows:
- Total bandwidth
- Used bandwidth
- Remaining bandwidth
- Requests total
- Requests successful
- Last request time, or “No usage recorded yet.”

No internal mode or multiplier labels are shown.

### Proxy Auth

1. **View credentials** – shows the proxy username and password.
2. **Edit credentials** – lets you change the proxy username/password.
3. **Back**

### IP Authorization

1. **List authorized IPs**
2. **Add IP**
3. **Remove IP**
4. **Back**

Use this if you want to connect to the proxies by IP allow-list instead of username/password.

### Change Admin Auth

Update the admin server URL or your user token. Changes are saved to the client config file.

## Config file

Location:

- Linux: `~/.prox_client_config.json`
- Windows: `C:\Users\<you>\.prox_client_config.json`

Example:

```json
{
  "server_url": "http://65.98.5.206:5000",
  "token": "your-user-token"
}
```

## Troubleshooting

**Connection refused**
- Check the admin server URL and port.
- Make sure the server is running and reachable.
- The default port is `5000`.

**Invalid token**
- Use the token provided by the admin.
- Use `Change Admin Auth` to update it.

**Clipboard copy fails**
- Install `pyperclip` and, on Linux, `xclip` or `xsel`.
- You can still view credentials in the Proxy Auth screen and copy them manually.

**Windows curses / terminal issues**
- The client uses plain terminal input, so it works in PowerShell, CMD and Windows Terminal.
