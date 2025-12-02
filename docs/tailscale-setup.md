# Tailscale Sidecar Setup Guide

This guide walks you through setting up the Tailscale sidecar for the Recipe Pipeline API, enabling remote access from your iPhone and other devices.

## Overview

The Tailscale sidecar allows your Recipe Pipeline API to be accessible from any device on your Tailscale network, enabling the iOS Shortcuts integration.

## Prerequisites

1. **Tailscale Account**: Sign up at [tailscale.com](https://tailscale.com) (free tier is sufficient)
2. **Docker & Docker Compose**: Already installed (required for this setup)
3. **Tailscale Admin Access**: You'll need to generate an auth key

## Step 1: Get a Tailscale Auth Key

1. **Log in to Tailscale Admin Console**:
   - Go to [https://login.tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys)
   - Or: Tailscale Admin Console → Settings → Keys

2. **Generate a Reusable Auth Key**:
   - Click **"Generate auth key"**
   - Set **"Reusable"** to **ON** (allows container restarts without re-authenticating)
   - Set **"Ephemeral"** to **OFF** (we want persistent connection)
   - Set expiration (optional, or leave as "Never expires")
   - Click **"Generate key"**
   - **Copy the key immediately** (you won't be able to see it again!)

3. **Save the key securely**:
   - You'll use this in the `.env` file

## Step 2: Create Environment File

Create a `.env` file in the project root:

```bash
# From project root
touch .env
```

Edit `.env` and add your configuration:

```bash
# Tailscale Auth Key (get from https://login.tailscale.com/admin/settings/keys)
TS_AUTHKEY=tskey-auth-xxxxxxxxxxxxx-xxxxxxxxxxxxx

# Obsidian Vault Path (absolute path on your host machine)
VAULT_PATH=/path/to/your/obsidian/vault
```

**Important**: Replace the placeholder values:

- `TS_AUTHKEY`: Your actual Tailscale auth key from Step 1
- `VAULT_PATH`: Full path to your Obsidian vault directory

## Step 3: Verify Docker Compose Configuration

The `docker-compose.yml` is already configured with:

- Tailscale sidecar service
- Recipe API service using Tailscale network
- Hostname set to `recipe-ingest` (customizable)

You can verify the configuration:

```bash
# Check docker-compose.yml
cat docker-compose.yml
```

Key settings:

- `hostname: recipe-ingest` - This will be your Tailscale hostname
- `network_mode: "service:tailscale"` - API uses Tailscale network
- `TS_AUTHKEY=${TS_AUTHKEY}` - Reads from .env file

## Step 4: Start the Services

1. **Build and start containers**:

   ```bash
   docker-compose up -d
   ```

2. **Check container status**:

   ```bash
   docker ps
   ```

   You should see both containers running:
   - `recipe-ingest-api`
   - `recipe-ingest-tailscale`

3. **Check Tailscale logs**:

   ```bash
   docker logs recipe-ingest-tailscale
   ```

   Look for:
   - `Successfully authenticated` or similar success message
   - Any error messages

4. **Verify Tailscale connection**:

   ```bash
   docker exec recipe-ingest-tailscale tailscale status
   ```

   You should see the device listed with hostname `recipe-ingest` and an IP address (100.x.x.x format).

## Step 5: Verify API is Accessible

### From Your Home PC

```bash
# Get the Tailscale IP
docker exec recipe-ingest-tailscale tailscale status

# Test health endpoint (using localhost since we're on the same machine)
curl http://localhost:8000/api/v1/health
```

### From Your iPhone (via Tailscale)

1. **Ensure iPhone is connected to Tailscale**:
   - Open Tailscale app on iPhone
   - Make sure you're logged in and connected

2. **Test API access**:
   - Open Safari on iPhone
   - Navigate to: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/health` (use your Tailscale MagicDNS domain)
   - You should see a JSON response
   - **Note**: The format is `recipe-ingest.<your-tailnet>.ts.net`. Get your domain with: `docker exec recipe-ingest-tailscale tailscale status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['Self']['DNSName'])"`

3. **If hostname doesn't work, try alternatives**:
   - Short hostname: `http://recipe-ingest:8000/api/v1/health` (if MagicDNS is enabled)
   - IP address: Get the IP from `docker exec recipe-ingest-tailscale tailscale status` and try `http://100.x.x.x:8000/api/v1/health`

## Step 6: Get Connection Info

Use the helper script to get your Tailscale connection details:

```bash
./scripts/get-tailscale-info.sh
```

This will show:

- Tailscale hostname
- IP address
- API URLs to use in your iOS Shortcut

## Troubleshooting

### Container Won't Start

**Check logs**:

```bash
docker logs recipe-ingest-tailscale
docker logs recipe-ingest-api
```

**Common issues**:

- **"TS_AUTHKEY not set"**: Make sure `.env` file exists and has `TS_AUTHKEY=...`
- **"Permission denied"**: May need to run with `sudo` or fix Docker permissions
- **"Network error"**: Check Docker network configuration

### Tailscale Not Connecting

**Check auth key**:

```bash
# Verify TS_AUTHKEY is set in container
docker exec recipe-ingest-tailscale env | grep TS_AUTHKEY
```

**Check Tailscale status**:

```bash
docker exec recipe-ingest-tailscale tailscale status
```

**If not connected**:

- Verify auth key is correct in `.env`
- Check auth key hasn't expired
- Check Tailscale admin console to see if device appears
- Restart container: `docker-compose restart tailscale`

### API Not Accessible from iPhone

**Check Tailscale on iPhone**:

- Is Tailscale app running?
- Is iPhone connected to Tailscale network?
- Can you see `recipe-ingest` device in Tailscale app?

**Check firewall**:

- Port 8000 should be accessible via Tailscale
- Check if any firewall rules are blocking

**Try IP instead of hostname**:

- Get IP: `docker exec recipe-ingest-tailscale tailscale status`
- Use IP in URL: `http://100.x.x.x:8000/api/v1/health`

### Hostname Not Resolving

If `recipe-ingest` hostname doesn't work:

1. **Use IP address instead** (get from `tailscale status`)
2. **Check Tailscale DNS settings**:
   - Admin console → DNS
   - Ensure MagicDNS is enabled
3. **Wait a few minutes** after container start (DNS propagation)

## Security Considerations

1. **Auth Key Security**:
   - Never commit `.env` file to git (should be in `.gitignore`)
   - Keep auth key secure
   - Regenerate if compromised

2. **Network Access**:
   - Only devices on your Tailscale network can access the API
   - Tailscale uses zero-trust model (secure by default)

3. **Future Enhancements**:
   - Add API key authentication (optional)
   - Use Tailscale ACLs for fine-grained access control

## Next Steps

Once Tailscale is set up:

1. ✅ Verify API is accessible from iPhone
2. ✅ Get your Tailscale hostname/IP
3. ✅ Set up iOS Shortcut (see `docs/ios-shortcuts-setup.md`)

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart Tailscale container
docker-compose restart tailscale

# Check Tailscale status
docker exec recipe-ingest-tailscale tailscale status

# Get connection info
./scripts/get-tailscale-info.sh

# Test API from remote device
./scripts/test-api-remote.sh recipe-ingest
```
