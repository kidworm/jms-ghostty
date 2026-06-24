# jms-ghostty

A lightweight CLI tool that connects to JumpServer, lists your assets, and opens Ghostty SSH sessions using system OpenSSH.

## Why

JumpServer Client is great for browsing assets, but it hardcodes iTerm2 as the terminal. If you prefer [Ghostty](https://ghostty.org), `jms-ghostty` bridges the gap: it talks to the JumpServer REST API directly and launches Ghostty with OpenSSH sessions through KoKo.

## Prerequisites

- Python 3
- [Ghostty](https://ghostty.org) installed

## Quick Start

```bash
# 1. First run — configure credentials
python3 jms_ghostty.py --configure

# 2. Interactive asset browser
python3 jms_ghostty.py

# 3. Search + connect
python3 jms_ghostty.py --search "prod"
```

## How It Works

1. Authenticates with JumpServer REST API (MFA supported)
2. Lists your permitted assets
3. Gets a connection token via `/api/v1/authentication/connection-token/`
4. Constructs the SSH command: `/usr/bin/ssh -p {port} JMS-{token_id}@{host}`
5. Copies the one-time connection token to the clipboard for the SSH password prompt
6. Launches Ghostty with the command

OpenSSH does not accept passwords as command-line arguments, so the token is copied to the clipboard instead of being embedded in the SSH command.

## License

MIT
