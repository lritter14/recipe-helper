# iOS Shortcuts Implementation Summary

## What's Already Done ✅

The API is already configured to support iOS Shortcuts integration:

1. **CORS Enabled**: API accepts requests from any origin (configured in `src/recipe_ingest/api/app.py`)
2. **Instagram Support**: API endpoint `/api/v1/recipes` accepts Instagram URLs
3. **Auto-detection**: API automatically detects Instagram URLs even if format is "text"
4. **Error Handling**: Proper error responses for troubleshooting

## What You Need to Do

### 1. Ensure Services Are Running

```bash
# Check if Docker containers are running
docker ps

# If not running, start them
docker-compose up -d

# Check logs if needed
docker logs recipe-ingest-api
docker logs recipe-ingest-tailscale
```

### 2. Get Your Tailscale Hostname/IP

```bash
# Run the helper script
./scripts/get-tailscale-info.sh

# Or manually
docker exec recipe-ingest-tailscale tailscale status
```

This will show you the URL to use in your Shortcut (e.g., `http://recipe-ingest.tailae97b1.ts.net:8000`)

**Note**: Use your Tailscale MagicDNS domain. Get it with:

```bash
docker exec recipe-ingest-tailscale tailscale status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['Self']['DNSName'])"
```

### 3. Test API Accessibility

From your iPhone (connected to Tailscale):

1. Open Safari
2. Navigate to: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/health` (use your Tailscale MagicDNS domain)
3. You should see a JSON response

Or run the test script from a device on the Tailscale network:

```bash
./scripts/test-api-remote.sh recipe-ingest.tailae97b1.ts.net
```

### 4. Create the iOS Shortcut

Follow the detailed guide: [`docs/ios-shortcuts-setup.md`](./ios-shortcuts-setup.md)

Quick version:

1. Open Shortcuts app
2. Create new shortcut: "Add Recipe"
3. Add actions:
   - Receive Input (URLs)
   - Get URLs from Input
   - Get Item from List (First Item)
   - Get Contents of URL (POST to `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/recipes` - use your Tailscale MagicDNS domain)
   - Show Notification
4. Enable in Share Sheet

### 5. Test End-to-End

1. Open Instagram on iPhone
2. Find a recipe post
3. Tap Share → "Add Recipe"
4. Check notification
5. Verify recipe in Obsidian vault

## Code Changes Required

**None!** The API already supports this. No code changes needed.

## Optional Enhancements (Future)

If you want to add these later:

1. **API Key Authentication**: Add simple token auth for extra security
2. **Better Error Messages**: More detailed error responses for Shortcuts
3. **Webhook Notifications**: Push notifications when recipe is added
4. **Preview Mode**: Show recipe preview before saving (already supported via `preview: true`)

## Troubleshooting

### API Not Accessible

- Check Tailscale connection on iPhone
- Verify Docker container is running
- Check container logs: `docker logs recipe-ingest-api`
- Try using IP address instead of hostname

### Shortcut Fails

- Verify URL variable is correctly inserted in JSON body
- Check that Content-Type header is set
- Test the API endpoint directly with curl:

  ```bash
  curl -X POST http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/recipes \
    -H "Content-Type: application/json" \
    -d '{"input": "https://www.instagram.com/p/EXAMPLE", "format": "instagram"}'
  ```

  (Replace with your actual Tailscale MagicDNS domain)

### Recipe Not Appearing

- Check API logs:

  ```bash
  docker logs recipe-ingest-api
  ```

- Verify vault path is correct in container
- Verify vault path is correct in container
- Check file permissions on vault directory

## Files Created

- `docs/ios-shortcuts-setup.md` - Detailed setup guide
- `docs/ios-shortcuts-quick-reference.md` - Quick reference card
- `scripts/test-api-remote.sh` - Test API accessibility
- `scripts/get-tailscale-info.sh` - Get Tailscale connection info

## Next Steps

1. ✅ Verify services are running
2. ✅ Get Tailscale hostname
3. ✅ Test API accessibility
4. ✅ Create iOS Shortcut
5. ✅ Test with real Instagram post
