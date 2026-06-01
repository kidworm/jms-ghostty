#!/usr/bin/env python3
"""
jms-ghostty — JumpServer → Ghostty Launcher
Log into JumpServer, browse assets, open Ghostty SSH sessions.
"""

import json, os, subprocess, sys, ssl, urllib.request, urllib.error, argparse
from pathlib import Path
from urllib.parse import urlparse

CONFIG_DIR = Path.home() / ".jms-ghostty"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

# JumpServer Client binary path
JMS_CLIENT_BIN = "/Applications/JumpServerClient.app/Contents/Resources/darwin/client"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def api_request(url, method="GET", data=None, token=None, timeout=15):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": str(e.code)}
    except Exception as e:
        return {"error": str(e)}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_token():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f).get("token")
    return None


def save_token(token):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({"token": token}, f)


def login(base_url, config):
    username = config.get("username") or input("Username: ").strip()
    password = config.get("password") or input("Password: ").strip()
    config.setdefault("username", username)
    config.setdefault("password", password)
    config.setdefault("base_url", base_url)
    save_config(config)

    url = f"{base_url}/api/v1/authentication/auth/"
    print(f"Logging in to {base_url} as {username}...")

    resp = api_request(url, method="POST", data={"username": username, "password": password})
    if "token" in resp:
        save_token(resp["token"])
        return resp["token"]

    msg = str(resp.get("msg") or resp.get("error") or "")
    if "mfa" in msg.lower():
        print(f"  MFA required ({resp.get('msg') or resp.get('error')})")
        mfa_data = resp.get("data", {})
        code = input("MFA code: ").strip()
        mfa_url = mfa_data.get("url", "")
        if mfa_url:
            if mfa_url.startswith("/"):
                mfa_url = base_url + mfa_url
            mfa_resp = api_request(mfa_url, method="POST", data={
                "code": code, "type": (mfa_data.get("choices") or ["otp"])[0]
            })
            if mfa_resp.get("msg") == "ok" or not mfa_resp.get("error"):
                resp = api_request(url, method="POST",
                    data={"username": username, "password": password})
                if "token" in resp:
                    save_token(resp["token"])
                    return resp["token"]
        resp = api_request(url, method="POST",
            data={"username": username, "password": password, "code": code})
        if "token" in resp:
            save_token(resp["token"])
            return resp["token"]

    print(f"Login failed: {resp}")
    sys.exit(1)


def list_assets(base_url, token):
    url = f"{base_url}/api/v1/assets/assets/"
    resp = api_request(url, token=token)
    if isinstance(resp, list):
        return resp
    elif isinstance(resp, dict):
        return resp.get("results", [])
    return []


def get_koko_port(base_url, token):
    """Get KoKo SSH port from JumpServer endpoint configuration."""
    url = f"{base_url}/api/v1/terminal/endpoints/"
    resp = api_request(url, token=token)
    results = resp if isinstance(resp, list) else resp.get("results", [])
    for ep in results:
        port = ep.get("ssh_port", 0)
        if port:
            return port
    return 2222


def display_assets(assets, search=None):
    if search:
        assets = [a for a in assets if search.lower() in a.get("name", "").lower()]
    if not assets:
        print("No assets found.")
        return None

    print(f"\n{'#':<4} {'Name':<35} {'Address':<22} {'Protocols':<15}")
    print("-" * 76)
    for i, asset in enumerate(assets):
        name = (asset.get("name") or "N/A")[:33]
        addr = (asset.get("address") or "N/A")[:20]
        protos = asset.get("protocols") or []
        if isinstance(protos, list):
            names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in protos]
            protos = ", ".join(names)
        elif isinstance(protos, str):
            pass
        else:
            protos = "ssh"
        print(f"{i+1:<4} {name:<35} {addr:<22} {str(protos):<15}")
    return assets


def interactive_pick(assets):
    while True:
        try:
            choice = input(f"\nPick an asset [1-{len(assets)}] or 'q': ").strip()
            if choice.lower() == 'q':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(assets):
                return assets[idx]
        except (ValueError, IndexError):
            pass
        print("Invalid choice.")


def main():
    parser = argparse.ArgumentParser(description="JumpServer → Ghostty Launcher")
    parser.add_argument("--configure", action="store_true", help="Re-configure credentials")
    parser.add_argument("--search", type=str, help="Filter assets by name")
    parser.add_argument("--connect", type=str, help="Connect by asset ID")
    parser.add_argument("--url", type=str, help="JumpServer URL")
    args = parser.parse_args()

    if args.configure:
        base_url = input("JumpServer URL: ").strip().rstrip("/")
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        save_config({"base_url": base_url, "username": username, "password": password})
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        print("✓ Configured")
        return

    config = load_config()
    base_url = args.url or config.get("base_url") or input("JumpServer URL: ").strip().rstrip("/")

    # Auth
    token = load_token()
    if token:
        test = api_request(f"{base_url}/api/v1/assets/assets/?limit=1", token=token)
        if isinstance(test, dict) and "error" in test:
            print("Token expired, re-authenticating...")
            token = None
    if not token:
        token = login(base_url, config)

    # Assets
    print("Fetching assets...")
    assets = list_assets(base_url, token)
    if not assets:
        print("No assets found.")
        sys.exit(1)

    # Pick asset
    if args.connect:
        selected = next((a for a in assets if str(a.get("id")) == args.connect), None)
        if not selected:
            print(f"Asset {args.connect} not found.")
            sys.exit(1)
    else:
        display_assets(assets, search=args.search)
        selected = interactive_pick(assets)
        if not selected:
            print("Cancelled.")
            return

    asset_id = selected["id"]
    asset_name = selected.get("name", "N/A")
    print(f"\nConnecting to: {asset_name}")

    # Get account for this asset
    accounts_url = f"{base_url}/api/v1/accounts/accounts/?asset={asset_id}"
    accounts_resp = api_request(accounts_url, token=token)
    accounts = accounts_resp if isinstance(accounts_resp, list) else accounts_resp.get("results", [])
    account_id = accounts[0]["id"] if accounts else None
    if not account_id:
        print("No system account found for this asset.")
        sys.exit(1)

    # Get connection token
    ct_url = f"{base_url}/api/v1/authentication/connection-token/"
    ct_resp = api_request(ct_url, method="POST", data={
        "asset": asset_id, "account": account_id, "connect_method": "ssh_client"
    }, token=token)

    if "error" in ct_resp:
        print(f"Connection token error: {ct_resp}")
        sys.exit(1)

    token_id = ct_resp["id"]
    token_value = ct_resp["value"]

    # Get KoKo host and port
    jms_host = urlparse(base_url).hostname or "192.168.105.96"
    koko_port = get_koko_port(base_url, token)

    # Build the SSH command (exactly like JumpServer Client)
    ssh_username = f"JMS-{token_id}"
    cmd_parts = [
        JMS_CLIENT_BIN, "ssh",
        f"{ssh_username}@{jms_host}",
        "-p", str(koko_port),
        "-P", token_value,
    ]
    cmd_str = " ".join(cmd_parts)
    print(f"  {cmd_str}")

    # Launch Ghostty
    subprocess.run([
        "open", "-na", "Ghostty.app", "--args",
        "--command=" + cmd_str
    ])
    print(f"✓ Launched Ghostty → {asset_name}")


if __name__ == "__main__":
    main()
