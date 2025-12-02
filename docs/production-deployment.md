# Production Deployment Guide

This guide covers deploying Recipe Helper in a production home server environment.

## Overview

The production docker-compose configuration (`docker-compose.prod.yml`) includes:

- Resource limits and reservations
- Logging with rotation
- Health checks
- Network isolation
- Security best practices
- Persistent data volumes

## Prerequisites

- Docker and Docker Compose installed
- Sufficient disk space for:
  - Ollama models (several GB per model)
  - Obsidian vault
  - Container logs
- Minimum 4GB RAM (8GB+ recommended)
- CPU with 2+ cores

## Quick Start

1. **Copy environment template:**

```bash
cp .env.example .env
```

2. **Edit `.env` with your configuration:**

```bash
# Required: Set your Obsidian vault path (use absolute path)
VAULT_PATH=/path/to/your/obsidian/vault

# Optional: Adjust other settings
LLM_MODEL=llama3.1:8b
LOG_LEVEL=INFO
```

3. **Start services:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. **Check service status:**

```bash
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## Configuration

### Environment Variables

All configuration is managed via the `.env` file. Key variables:

- `VAULT_PATH`: Absolute path to your Obsidian vault (required)
- `VAULT_RECIPES_DIR`: Subdirectory for recipes (default: `personal/recipes`)
- `LLM_MODEL`: Ollama model to use (default: `llama3.1:8b`)
- `LLM_TIMEOUT`: Request timeout in seconds (default: `120`)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

### Resource Limits

Default resource limits are set in `docker-compose.prod.yml`:

**Ollama:**
- CPU limit: 4 cores
- Memory limit: 8GB
- CPU reservation: 1 core
- Memory reservation: 2GB

**Recipe API:**
- CPU limit: 2 cores
- Memory limit: 1GB
- CPU reservation: 0.5 cores
- Memory reservation: 256MB

Adjust these based on your hardware in the `deploy.resources` section.

### Network Configuration

By default, services are only exposed on the internal Docker network. To access the API externally:

1. **Option 1: Use a reverse proxy (recommended)**

   Set up nginx, Traefik, or Caddy to proxy requests:

```nginx
# nginx example
server {
    listen 80;
    server_name recipe-api.local;

    location / {
        proxy_pass http://localhost:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **Option 2: Bind to localhost only**

   Uncomment the ports section in `docker-compose.prod.yml`:

```yaml
ports:
  - "127.0.0.1:8100:8100"
```

3. **Option 3: Use Tailscale**

   Access via Tailscale VPN (see `docs/tailscale-setup.md`)

## Security Considerations

### File Permissions

Ensure the Obsidian vault directory has appropriate permissions:

```bash
# Set ownership (adjust user/group as needed)
sudo chown -R $USER:$USER /path/to/vault

# Set permissions
chmod -R 755 /path/to/vault
```

### Network Security

- Services communicate via internal Docker network
- No external ports exposed by default
- Use reverse proxy with TLS for external access
- Consider firewall rules to restrict access

### Container Security

- Containers run as non-root users (configured in Dockerfile)
- Read-only root filesystem can be enabled (commented out - uncomment if compatible)
- Resource limits prevent resource exhaustion attacks

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f recipe-api
docker-compose -f docker-compose.prod.yml logs -f ollama
```

### Log Rotation

Logs are automatically rotated:
- Max size: 10MB per file
- Max files: 3 (keeps ~30MB total)
- Compression: enabled

Logs are stored in Docker's default location (usually `/var/lib/docker/containers/`).

### Health Checks

Health checks are configured for both services:

- **Ollama**: Checks if service is listening on port 11434
- **Recipe API**: Checks `/api/v1/health` endpoint

View health status:

```bash
docker-compose -f docker-compose.prod.yml ps
```

## Persistent Data

### Ollama Data

Ollama models and data are stored in the `ollama_data` volume. To backup:

```bash
# Find volume location
docker volume inspect recipe-helper_ollama_data

# Backup
docker run --rm -v recipe-helper_ollama_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/ollama-backup.tar.gz -C /data .
```

### Obsidian Vault

The vault is mounted from your host filesystem, so it's automatically persisted. Ensure you have regular backups of your vault directory.

## Updating

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Update Ollama

```bash
# Pull latest Ollama image
docker-compose -f docker-compose.prod.yml pull ollama

# Restart service
docker-compose -f docker-compose.prod.yml up -d ollama
```

### Update Models

Access Ollama CLI:

```bash
docker exec -it recipe-ollama ollama pull llama3.1:8b
docker exec -it recipe-ollama ollama list
```

## Troubleshooting

### Services Won't Start

1. Check logs:

```bash
docker-compose -f docker-compose.prod.yml logs
```

2. Verify environment variables:

```bash
docker-compose -f docker-compose.prod.yml config
```

3. Check disk space:

```bash
df -h
docker system df
```

### API Can't Connect to Ollama

1. Verify Ollama is healthy:

```bash
docker-compose -f docker-compose.prod.yml ps ollama
```

2. Test connection:

```bash
docker exec -it recipe-api python -c "import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/tags').read())"
```

3. Check network:

```bash
docker network inspect recipe-helper_recipe-network
```

### High Memory Usage

1. Check resource usage:

```bash
docker stats
```

2. Adjust resource limits in `docker-compose.prod.yml`
3. Consider using a smaller LLM model
4. Reduce Ollama's context window if configurable

### Permission Errors

If you see permission errors accessing the vault:

```bash
# Check vault permissions
ls -la /path/to/vault

# Fix ownership (adjust user/group)
sudo chown -R $USER:$USER /path/to/vault
```

## Backup Strategy

### Recommended Backups

1. **Obsidian Vault**: Regular backups (daily/weekly) using your preferred method
2. **Ollama Data**: Backup volume periodically (models are large, so less frequent)
3. **Configuration**: Backup `.env` file and `docker-compose.prod.yml`

### Automated Backups

Consider setting up automated backups using cron or a backup tool:

```bash
# Example cron job for vault backup
0 2 * * * tar -czf /backups/vault-$(date +\%Y\%m\%d).tar.gz /path/to/vault
```

## Performance Tuning

### For Better Performance

1. **Use GPU acceleration** (if available):

   Modify Ollama service to use GPU:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

2. **Adjust model size**: Use smaller models if memory constrained
3. **Increase timeouts**: For slower hardware, increase `LLM_TIMEOUT`
4. **Optimize Python**: Already configured with `PYTHONUNBUFFERED` and `PYTHONDONTWRITEBYTECODE`

## Maintenance

### Regular Tasks

- **Weekly**: Review logs for errors
- **Monthly**: Update Docker images
- **Quarterly**: Review and adjust resource limits
- **As needed**: Clean up unused Docker resources

### Cleanup Commands

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (be careful!)
docker volume prune

# System cleanup
docker system prune
```

## Support

For issues or questions:

1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review this documentation
3. Check GitHub issues
4. Review application logs in the vault or container logs

