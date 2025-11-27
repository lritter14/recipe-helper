# Ollama Docker Access Setup

## Problem

When the recipe API container uses `network_mode: "service:tailscale"`, it cannot access Ollama running on the host machine using `host.docker.internal` because it's on the Tailscale network namespace.

## Solution

Configure Ollama to listen on all network interfaces (0.0.0.0) so it's accessible via the Tailscale network.

## Steps

### 1. Configure Ollama to Listen on All Interfaces

On macOS, Ollama runs as an app. To make it listen on all interfaces:

**Option A: Set Environment Variable (Recommended)**

1. Quit Ollama (if running):
   ```bash
   pkill -f ollama
   ```

2. Set the environment variable and start Ollama:
   ```bash
   export OLLAMA_HOST=0.0.0.0:11434
   ollama serve
   ```

   Or add to your `~/.zshrc` or `~/.bash_profile`:
   ```bash
   export OLLAMA_HOST=0.0.0.0:11434
   ```

3. Restart Ollama app (or run `ollama serve` in terminal)

**Option B: Use LaunchAgent (Persistent)**

Create `~/Library/LaunchAgents/com.ollama.env.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.env</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/launchctl</string>
        <string>setenv</string>
        <string>OLLAMA_HOST</string>
        <string>0.0.0.0:11434</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.ollama.env.plist
launchctl start com.ollama.env
```

### 2. Verify Ollama is Listening on All Interfaces

```bash
lsof -i :11434
# Should show: TCP *:11434 (LISTEN) or TCP 0.0.0.0:11434 (LISTEN)
```

### 3. Update Recipe API Configuration

The config file should use your host machine's Tailscale hostname or IP:

```yaml
llm:
  endpoint: "http://macbook-air-1:11434"  # Your Tailscale hostname
  # OR
  endpoint: "http://100.66.178.124:11434"  # Your Tailscale IP
```

### 4. Test Connection from Container

```bash
docker exec recipe-ingest-api curl -s http://macbook-air-1:11434/api/tags
```

### 5. Restart API Container

```bash
docker-compose restart recipe-api
```

## Security Note

⚠️ **Warning**: Making Ollama listen on `0.0.0.0` exposes it to all network interfaces. Since you're using Tailscale (a private VPN), this is relatively safe, but ensure:

1. Your Tailscale network is properly secured
2. Only trusted devices are on your Tailscale network
3. Consider using Tailscale ACLs to restrict access if needed

## Alternative: Use Host Network Mode (Not Recommended)

If the above doesn't work, you could modify docker-compose.yml to use host networking, but this conflicts with Tailscale's network mode and is not recommended.
