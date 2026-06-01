# jms-ghostty

A lightweight CLI tool that connects to JumpServer, lists your assets, and opens Ghostty SSH sessions — without needing the JumpServer Client running.

## Why

JumpServer Client is great for browsing assets, but it hardcodes iTerm2 as the terminal. If you prefer [Ghostty](https://ghostty.org), you're out of luck. `jms-ghostty` bridges the gap: it talks to the JumpServer REST API directly and launches Ghostty with proper SSH sessions through KoKo.

## Prerequisites

- Python 3
- [JumpServer Client](https://github.com/jumpserver/jumpserver) installed (the tool uses its bundled `client` SSH binary)
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
4. Constructs the SSH command: `{jms_client} ssh JMS-{token_id}@{host} -p {port} -P {token}`
5. Launches Ghostty with the command

The SSH client binary (`darwin/client`) comes bundled with JumpServer Client — it's JumpServer's Go-based SSH tool that handles KoKo authentication properly.

## License

MIT
