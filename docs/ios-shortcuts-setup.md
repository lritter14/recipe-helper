# iOS Shortcuts Setup Guide

This guide walks you through setting up an iOS Shortcut to share Instagram posts directly to your Recipe Pipeline.

## Prerequisites

1. **API Server Running**: Your Recipe Pipeline API must be running and accessible via Tailscale
2. **Tailscale Access**: Your iPhone must be connected to the same Tailscale network
3. **Tailscale Hostname**: Know your Tailscale hostname (default: `recipe-ingest`)

## Step 1: Verify API is Accessible

First, test that your API is accessible from your iPhone:

1. On your iPhone, open Safari
2. Navigate to: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/health`
   - **Note**: Use your actual Tailscale MagicDNS domain. The format is `recipe-ingest.<your-tailnet>.ts.net`
   - You can also try the short hostname `recipe-ingest:8000` if MagicDNS is enabled
3. You should see a JSON response like:

   ```json
   {
     "status": "healthy",
     "ollama_connected": true,
     "vault_accessible": true
   }
   ```

If this doesn't work, check:

- Is your iPhone connected to Tailscale?
- Is the Docker container running? (`docker ps` to check)
- What's the actual Tailscale hostname? (Check Tailscale admin console or run `docker exec recipe-ingest-tailscale tailscale status`)

## Step 2: Get Your API URL

Your API URL will be one of:

- `http://recipe-ingest.tailae97b1.ts.net:8000` (Tailscale MagicDNS domain - **recommended**)
- `http://recipe-ingest:8000` (short hostname - works if MagicDNS is enabled)
- `http://<tailscale-ip>:8000` (IP address - use if hostname doesn't resolve)

To find your Tailscale hostname/IP:

```bash
# Get the full MagicDNS domain (recommended)
docker exec recipe-ingest-tailscale tailscale status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['Self']['DNSName'])"

# Or check Tailscale status for hostname and IP
docker exec recipe-ingest-tailscale tailscale status
```

**Note**: The MagicDNS domain format is `recipe-ingest.<your-tailnet>.ts.net`. Write down this URL - you'll need it for the Shortcut.

## Step 3: Create the iOS Shortcut

1. **Open Shortcuts App** on your iPhone
2. **Tap the "+" button** (top right) to create a new shortcut
3. **Name it**: "Add Recipe" (or whatever you prefer)
4. **Tap "Add Action"**

### Configure the Shortcut Actions

Add these actions in order:

#### Action 1: Accept Input

- Search for "Get Contents of Input"
- Or search for "Receive Input"
- Set input type to: **URLs**

#### Action 2: Get URL

- Search for "Get URLs from Input"
- This extracts the URL from the share sheet

#### Action 3: Get First Item

- Search for "Get Item from List"
- Set to: **First Item** (in case multiple URLs are shared)

#### Action 4: Get URL Contents (Optional)

- Search for "Get Contents of URL"
- This step is optional - it helps extract the Instagram URL if the share sheet provides a different format
- You can skip this if Instagram URLs are already in the correct format

#### Action 5: HTTP Request

- Search for "Get Contents of URL"
- Tap the method dropdown and change to **POST**
- Set URL to: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/recipes` (use your actual Tailscale MagicDNS domain)
- Tap "Show More"
- Set Request Body to: **Request Body**
- Set Request Body Type to: **JSON**
- In the JSON body, enter:

  ```json
  {
    "input": "[URL from Step 3]",
    "format": "instagram"
  }
  ```

- Set Headers:
  - Key: `Content-Type`
  - Value: `application/json`

**Important**: Replace `[URL from Step 3]` with the actual variable from the "Get Item from List" action. Tap the variable name to insert it.

#### Action 6: Show Notification

- Search for "Show Notification"
- Set title to: "Recipe Added" (or customize)
- Set body to: The response from the HTTP request (use the variable from Step 5)

### Alternative: Simpler Version (If URL extraction is tricky)

If the above is too complex, here's a simpler approach:

1. **Accept Input**: URLs
2. **Get URLs from Input**
3. **Get Item from List**: First Item
4. **Text**: Create a text block with:

   ```json
   {"input": "[URL]", "format": "instagram"}
   ```

   (Replace `[URL]` with the variable from step 3)
5. **Get Contents of URL**:
   - Method: POST
   - URL: `http://recipe-ingest.tailae97b1.ts.net:8000/api/v1/recipes` (use your Tailscale MagicDNS domain)
   - Request Body: The text from step 4
   - Headers: `Content-Type: application/json`
6. **Show Notification**: Show the result

## Step 4: Configure Share Sheet

1. In your Shortcut, tap the **settings icon** (three dots at top)
2. Tap **"Add to Share Sheet"**
3. Enable **"Show in Share Sheet"**
4. Set **"Receive Input"** to: **URLs**
5. Optionally customize the icon and name

## Step 5: Test the Shortcut

1. Open Instagram on your iPhone
2. Find a recipe post
3. Tap the **Share button** (arrow icon)
4. Scroll down and tap **"Add Recipe"** (or your shortcut name)
5. The shortcut should run and show a notification

### Troubleshooting

#### "Could not connect to server"

- Verify Tailscale is connected on iPhone
- Check the API URL is correct
- Try using the Tailscale IP instead of hostname

#### "Invalid recipe input"

- The URL might not be in the right format
- Try sharing the Instagram post link directly (copy link first)

#### "Service temporarily unavailable"

- Check if the Docker container is running: `docker ps`
- Check container logs: `docker logs recipe-ingest-api`
- Verify LLM server is running

## Step 6: Verify Recipe Was Added

1. Open your Obsidian vault
2. Navigate to `personal/recipes/`
3. You should see a new markdown file with the recipe

## Advanced: Error Handling

To add better error handling to your shortcut:

1. After the HTTP request, add an **"If"** action
2. Check if the response contains `"status": "success"`
3. If yes: Show success notification
4. If no: Show error notification with the error message

## Security Note

The API is currently accessible to anyone on your Tailscale network. For additional security, you could:

1. Add API key authentication (future enhancement)
2. Use Tailscale ACLs to restrict access
3. Add rate limiting

For now, Tailscale's zero-trust model provides reasonable security for personal use.
