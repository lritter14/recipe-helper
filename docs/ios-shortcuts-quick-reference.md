# iOS Shortcuts Quick Reference

Quick setup checklist for iOS Shortcuts integration.

## Prerequisites Checklist

- [ ] Docker container running: `docker ps | grep recipe-ingest`
- [ ] Tailscale connected on iPhone
- [ ] API accessible: Test `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/health` in Safari (use your Tailscale MagicDNS domain)

## Get Your API URL

Run this script to get your Tailscale hostname/IP:

```bash
./scripts/get-tailscale-info.sh
```

Or manually:

```bash
docker exec recipe-ingest-tailscale tailscale status
```

## Shortcut Configuration

### Required Actions (in order)

1. **Receive Input** → Type: URLs
2. **Get URLs from Input**
3. **Get Item from List** → First Item
4. **Get Contents of URL**:
   - Method: **POST**
   - URL: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/recipes` (use your Tailscale MagicDNS domain)
   - Request Body: **Request Body**
   - Request Body Type: **JSON**
   - JSON Body:

     ```json
     {
       "input": "[URL variable from step 3]",
       "format": "instagram"
     }
     ```

   - Headers:
     - `Content-Type`: `application/json`
5. **Show Notification** → Show response

### Enable Share Sheet

- Settings → Add to Share Sheet → Enable
- Receive Input: URLs

## Test

1. Open Instagram
2. Share a recipe post
3. Select "Add Recipe" shortcut
4. Check notification for success/error
5. Verify recipe in Obsidian vault

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect | Check Tailscale on iPhone |
| Invalid input | Make sure URL variable is inserted correctly |
| Service unavailable | Check Docker logs: `docker logs recipe-ingest-api` |

## API Endpoint Details

- **URL**: `POST http://<hostname>:8000/api/v1/recipes`
- **Headers**: `Content-Type: application/json`
- **Body**:

  ```json
  {
    "input": "https://www.instagram.com/p/...",
    "format": "instagram",
    "preview": false
  }
  ```
