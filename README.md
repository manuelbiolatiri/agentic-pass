# Pass-MCP (`pass-mcp`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec](https://img.shields.io/badge/MCP-1.0.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`pass-mcp`** is an open-source **Model Context Protocol (MCP)** server and Python client for delegating and issuing **Apple Wallet (`.pkpass`)** and **Google Wallet** passes to AI agents (Claude Desktop, AutoGPT, LLMs).

Built with **FastAPI**, **Pydantic v2**, **httpx**, and Anthropic's official **`mcp` Python SDK**.

---

## ⚡ Quickstart

### 1. Installation

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

## 🎁 Daily Free Pass Tier & Licensing

* **10 Free Passes / Day**: Every installer/device receives **10 free pass issuances per day** automatically out-of-the-box (`pass_mcp/rate_limiter.py`). No API key or credit card required!
* **Unlimited Production Tier**: Set your `WALLETKIT_API_KEY` environment variable to connect to your live `walletKit` merchant account for unlimited pass signing:
  ```env
  WALLETKIT_API_KEY=wk_live_abc123...
  WALLETKIT_API_URL=https://api.walletkit.io
  ```

---

## 🧪 Testing

Run the automated test suite and over-the-wire conformance tests:

```bash
./venv/bin/pytest -v
```

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
> *"Issue an event ticket pass under a delegation mandate for agent_123."*

---

## 🌐 Running as an HTTP / FastAPI Gateway (Port 9000)

You can also run `pass-mcp` as a standalone web gateway:

```bash
# Start FastAPI gateway on port 9000
./venv/bin/uvicorn pass_mcp.api:app --port 9000 --reload
```

Test endpoint via `curl`:
```bash
curl -X POST http://localhost:9000/api/v1/mandates/issue \
  -H "Content-Type: application/json" \
  -d '{
    "principalId": "usr_human_demo",
    "agentId": "agent_ai_demo",
    "authorizationDetails": [
      {
        "type": "event_ticket",
        "pass_class": "event_ticket",
        "max_quantity": 2
      }
    ]
  }'
```

---

## 📜 Security & Delegation Invariants

`pass-mcp` enforces the 7 core agent delegation security invariants:
1. **Principal Binding**: Issued passes bind strictly to human principal (`sub`), never to agent actor (`act`).
2. **Proof-of-Possession**: Enforces `cnf` key thumbprints.
3. **Strict Scope Evaluation**: Evaluated exclusively from signed JWT `authorization_details`.
4. **Idempotency Engine**: `SHA256(mandate_jti || canonical_request_hash)` prevents duplicate pass issuance.
5. **Immutable Audit Ledger**: Every decision path logs to an append-only, cryptographically hash-chained ledger.
6. **Fail-Closed Escalation**: CIBA human-in-the-loop timeouts fail closed (`DENY`).
7. **Standards Compliant**: Built on RFC 8693, CIBA, and Model Context Protocol (MCP).
