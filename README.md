# Pass-MCP (`pass-mcp`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec](https://img.shields.io/badge/MCP-1.0.0-green.svg)](https://modelcontextprotocol.io/)
[![Smithery Badge](https://smithery.ai/badge/pass-mcp)](https://smithery.ai/server/pass-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`pass-mcp`** is an open-source **Model Context Protocol (MCP)** server and Python client for delegating, issuing, and managing **Apple Wallet (`.pkpass`)** and **Google Wallet** passes under signed RFC 8693 AI agent delegation tokens.

Built with **FastAPI**, **Pydantic v2**, **httpx**, and Anthropic's official **`mcp` Python SDK**.

---

## ⚡ Quickstart

### 1. Install via Smithery (1-Click Claude Desktop Installation)

```bash
npx -y @smithery/cli install pass-mcp --client claude
```

### 2. Manual Installation

```bash
git clone https://github.com/emmanuelbiolatiri/pass-mcp.git
cd pass-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode
pip install -e .
```

---

## 🛠 Available MCP Tools

`pass-mcp` exposes 8 core tools to Claude Desktop, AutoGPT, and LLM clients over Stdio transport. Every tool also accepts an optional `api_key` argument, which overrides the server's configured `WALLETKIT_API_KEY` for that single call — this lets one running `pass-mcp` instance act on behalf of a different merchant business per call, instead of being locked to whichever key it was started with.

| Tool Name | Parameters | Description |
|---|---|---|
| `issue_mandate` | `principal_id`, `agent_id`, `authorization_details`, `ttl_seconds`, `api_key` | Issue a signed RFC 8693 delegation mandate token for an AI agent. |
| `request_pass` | `mandate_token`, `pass_class`, `quantity`, `resource`, `spend`, `purpose`, `api_key` | Request Apple/Google Wallet pass issuance under a delegation token. |
| `get_holder_passes` | `external_user_id`, `mandate_token`, `api_key` | Retrieve all active digital wallet passes held by a human principal. |
| `lookup_pass` | `pass_id`, `api_key` | Query full details, status, and download URLs for a pass. |
| `check_mandate_status` | `mandate_token`, `api_key` | Inspect live status and remaining TTL of a delegation token. |
| `poll_escalation` | `auth_req_id`, `api_key` | Poll status of a pending CIBA human-in-the-loop escalation request. |
| `respond_to_escalation` | `auth_req_id`, `approved`, `reason`, `api_key` | Approve or deny a pending CIBA human-in-the-loop escalation (Human Principal action). |
| `revoke_mandate` | `jti`, `reason`, `api_key` | Revoke a mandate immediately by JTI, blocking any further enforcement under it. |

---

## 🖼️ Live Visual Pass Card & Barcode Previews

Pass responses automatically enrich outputs with live visual asset URLs:
* **Web Pass Preview**: `https://passera-web.vercel.app/p/{passId}`
* **Visual Card Image**: `https://api.passera.com/public/passes/{passId}/preview-card.png`
* **Barcode QR Code**: `https://api.passera.com/public/passes/{passId}/qr`
* **Apple Wallet (.pkpass)**: `https://api.passera.com/public/passes/{passId}/apple`
* **Google Wallet**: `https://api.passera.com/public/passes/{passId}/google`

Claude Desktop automatically renders the visual pass card image inline in chat responses!

---

## 🎁 Daily Pass Quota & Licensing

* **100 passes / day, per business**: `pass_mcp/rate_limiter.py` enforces a flat local quota of 100 pass issuances per day, tracked per merchant `api_key` (hashed, never stored in plaintext). With no key at all, the same 100/day quota applies per installer device instead. No API key or credit card required to try it out!
* **Bring your own merchant account**: Set your `WALLETKIT_API_KEY` environment variable (or pass `api_key` per tool call) to connect to your live merchant account:
  ```env
  WALLETKIT_API_KEY=wk_live_abc123...
  WALLETKIT_API_URL=https://passera-service-production.up.railway.app
  ```
  This is a client-side courtesy guard only — wallet-pass-api remains the source of truth for whether a key is actually valid and for any quota it enforces server-side.

---

## 🤖 Claude Desktop Configuration (`claude_desktop_config.json`)

Add `pass-mcp` to your Claude Desktop configuration file:
* **macOS Path**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pass-mcp": {
      "command": "/Users/emmanuelbiolatiri/Desktop/manuel/pass-mcp/venv/bin/pass-mcp",
      "env": {
        "WALLETKIT_API_URL": "http://localhost:3000"
      }
    }
  }
}
```

Restart Claude Desktop and prompt:
> *"Issue an event ticket mandate for usr_emmanuel with 2 passes, then request 1 pass."*

---

## 🧪 Testing

Run the automated test suite and over-the-wire conformance tests:

```bash
./venv/bin/pytest -v
```

---

## 🌐 Running as an HTTP / FastAPI Gateway (Port 9000)

You can also run `pass-mcp` as a standalone web gateway:

```bash
# Start FastAPI gateway on port 9000
./venv/bin/uvicorn pass_mcp.api:app --port 9000 --reload
```

---

## 📄 License

MIT License © Emmanuel Biolatiri
