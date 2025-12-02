# Tailscale Quick Start

Quick setup checklist for Tailscale sidecar integration.

## Prerequisites Checklist

- [ ] Tailscale account (sign up at tailscale.com)
- [ ] Docker and Docker Compose installed
- [ ] Obsidian vault path ready

## Setup Steps

### 1. Get Tailscale Auth Key (2 minutes)

1. Go to: https://login.tailscale.com/admin/settings/keys
2. Click "Generate auth key"
3. Set **Reusable: ON**
4. Set **Ephemeral: OFF**
5. Click "Generate key"
6. **Copy the key** (you won't see it again!)

### 2. Create .env File (1 minute)

Create `.env` in project root:

```bash
# Tailscale Auth Key
TS_AUTHKEY=tskey-auth-xxxxxxxxxxxxx-xxxxxxxxxxxxx

# Obsidian Vault Path (absolute path)
VAULT_PATH=/path/to/your/obsidian/vault
```

**Replace**:
- `TS_AUTHKEY` with your actual key from step 1
- `VAULT_PATH` with your actual vault path

### 3. Start Services (1 minute)

```bash
# Build and start
docker-compose up -d

# Check status
docker ps

# Check Tailscale logs
docker logs recipe-ingest-tailscale
```

### 4. Verify Connection (1 minute)

```bash
# Get Tailscale info
./scripts/get-tailscale-info.sh

# Or manually check
docker exec recipe-ingest-tailscale tailscale status
```

### 5. Test from iPhone (2 minutes)

1. Open Tailscale app on iPhone (ensure connected)
2. Open Safari
3. Navigate to: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/health` (use your Tailscale MagicDNS domain)
   - Get your domain: `docker exec recipe-ingest-tailscale tailscale status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['Self']['DNSName'])"`
4. Should see JSON response

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container won't start | Check `.env` file exists and has `TS_AUTHKEY` |
| Tailscale not connecting | Verify auth key is correct, check logs |
| Can't access from iPhone | Ensure iPhone is on Tailscale network |
| Hostname doesn't work | Use IP address from `tailscale status` |

## Next Steps

Once Tailscale is working:

1. ✅ Get your API URL: `./scripts/get-tailscale-info.sh`
2. ✅ Set up iOS Shortcut: See `docs/ios-shortcuts-setup.md`

## Full Documentation

For detailed setup and troubleshooting, see: `docs/tailscale-setup.md`
