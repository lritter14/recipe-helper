---
created: "2025-01-XX"
status: "draft"
---

# Mobile Integration Options

## Overview

Three approaches for integrating mobile sharing from Instagram posts to the recipe pipeline. User flow: See Instagram post → Press share button → Send to app → Recipe card created and written to Obsidian vault.

## Current State

- FastAPI endpoint: `POST /api/v1/recipes` accepts Instagram URLs
- Auto-detection of Instagram URLs (format: "text" or "instagram")
- Tailscale network for secure remote access
- Health check endpoint available

## Option 1: iOS Shortcuts Integration

### Option 1: Approach

Use the built-in iOS Shortcuts app to create a share sheet action that calls the API directly.

### Option 1: User Flow

1. User sees Instagram post
2. Taps share button → Selects "Add Recipe" shortcut
3. Shortcut extracts Instagram URL from share input
4. Shortcut makes HTTP POST to FastAPI endpoint via Tailscale
5. Shortcut shows notification with success/error
6. Recipe appears in Obsidian vault

### Option 1: Implementation

**iOS Shortcuts Setup:**

1. Create new shortcut named "Add Recipe"
2. Accept input: URLs
3. Get URL from input
4. Get contents of URL (to extract Instagram URL if needed)
5. HTTP POST to `https://<tailscale-hostname>:8000/api/v1/recipes`
   - Body: `{"input": "<instagram-url>", "format": "instagram"}`
   - Headers: `Content-Type: application/json`
6. Show notification with response status

**Backend Changes:**

- None required (API already supports this)
- Optional: Add simple authentication token for security

### Option 1: Pros

- Zero code development (just configure shortcut)
- Works immediately, no app store approval
- Native iOS integration
- Can be customized with additional logic (preview, error handling)
- Free

### Option 1: Cons

- Requires manual setup by each user
- Less polished UX (generic shortcut UI)
- Limited error handling visibility
- No offline queue
- iOS only

### Option 1: Security Considerations

- API accessible via Tailscale (already secure)
- Optional: Add API key authentication
- Shortcut stores Tailscale hostname (user configurable)

### Option 1: Effort

- Setup time: 15-30 minutes per user
- Maintenance: Minimal (only if API changes)

---

## Option 2: Native iOS Share Extension

### Option 2: Approach

Build a native iOS app with a share extension that appears in the iOS share sheet.

### Option 2: User Flow

1. User sees Instagram post
2. Taps share button → Sees "Recipe Pipeline" option in share sheet
3. Taps "Recipe Pipeline" → App extension opens
4. Extension shows preview/confirmation screen
5. User taps "Add Recipe" → Extension calls API
6. Extension shows success/error feedback
7. Recipe appears in Obsidian vault

### Option 2: Implementation

**iOS App Structure:**

- Main app (minimal, just for settings)
- Share extension target
- SwiftUI interface

**Share Extension:**

```swift
// Simplified example
class ShareViewController: UIViewController {
    func processInstagramURL(_ url: URL) {
        let apiURL = URL(string: "https://<tailscale-hostname>:8000/api/v1/recipes")!
        var request = URLRequest(url: apiURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = [
            "input": url.absoluteString,
            "format": "instagram"
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response, show notification
        }.resume()
    }
}
```

**Backend Changes:**

- None required (API already supports this)
- Optional: Add authentication endpoint for app registration

### Option 2: Pros

- Polished, native iOS experience
- Custom UI for preview/confirmation
- Can show recipe preview before saving
- Can handle errors gracefully with custom UI
- Can add offline queue for later processing
- Professional appearance

### Option 2: Cons

- Requires iOS development (Swift/SwiftUI)
- Requires Apple Developer account ($99/year)
- App store submission process
- More maintenance overhead
- iOS only

### Option 2: Security Considerations

- API accessible via Tailscale
- Can store API credentials in iOS Keychain
- Optional: OAuth or API key authentication

### Option 2: Effort

- Development: 1-2 weeks (Swift experience required)
- Maintenance: Ongoing (iOS updates, API changes)

---

## Option 3: Progressive Web App (PWA) with Share Target API

### Option 3: Approach

Build a web app that can be installed on mobile devices and registered as a share target.

### Option 3: User Flow

1. User installs PWA to home screen
2. User sees Instagram post
3. Taps share button → Sees "Recipe Pipeline" in share targets
4. Taps "Recipe Pipeline" → PWA opens with Instagram URL
5. PWA shows preview/confirmation
6. User taps "Add Recipe" → PWA calls API
7. PWA shows success/error feedback
8. Recipe appears in Obsidian vault

### Option 3: Implementation

**Web App Manifest:**

```json
{
  "name": "Recipe Pipeline",
  "short_name": "Recipes",
  "start_url": "/",
  "display": "standalone",
  "share_target": {
    "action": "/share",
    "method": "GET",
    "params": {
      "url": "url"
    }
  }
}
```

**Share Handler Page:**

```javascript
// /share route handler
async function handleShare() {
    const urlParams = new URLSearchParams(window.location.search);
    const instagramURL = urlParams.get('url');

    const response = await fetch('https://<tailscale-hostname>:8000/api/v1/recipes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            input: instagramURL,
            format: 'instagram'
        })
    });

    const result = await response.json();
    // Show success/error UI
}
```

**Backend Changes:**

- None required (API already supports this)
- Ensure CORS allows PWA origin
- Optional: Add authentication

### Option 3: Pros

- Cross-platform (iOS and Android)
- No app store submission
- Easy to update (just deploy web changes)
- Can reuse existing web UI code
- Works on desktop too
- Free (no developer account needed)

### Option 3: Cons

- Share Target API support varies by platform
  - iOS: Limited support (may need workaround)
  - Android: Full support
- Less native feel than native app
- Requires HTTPS (Tailscale provides this)
- May need fallback for iOS (URL scheme instead)

### Option 3: Security Considerations

- API accessible via Tailscale
- CORS configuration for PWA origin
- Optional: API key authentication

### Option 3: Effort

- Development: 3-5 days (web development)
- Maintenance: Low (web updates)

### iOS Limitations

iOS Safari has limited Share Target API support. Workaround options:

1. **URL Scheme Fallback**: Register custom URL scheme (`recipe-helper://share?url=...`)
   - Use Shortcuts to call URL scheme
   - Or use third-party app that supports URL schemes

2. **Copy to Clipboard**: PWA detects clipboard changes and processes
   - Less seamless but works

---

## Comparison Matrix

| Feature | iOS Shortcuts | Native iOS App | PWA |
|---------|---------------|----------------|-----|
| **Development Time** | 15-30 min | 1-2 weeks | 3-5 days |
| **Platform Support** | iOS only | iOS only | iOS + Android |
| **User Experience** | Basic | Excellent | Good |
| **Maintenance** | Low | Medium | Low |
| **Cost** | Free | $99/year | Free |
| **App Store** | No | Yes | No |
| **Offline Support** | No | Yes (possible) | Limited |
| **Custom UI** | No | Yes | Yes |
| **Setup Complexity** | Medium | Low (after install) | Low (after install) |

## Recommendation

**For MVP/Quick Win:** Option 1 (iOS Shortcuts)

- Fastest to implement
- Zero development overhead
- Good enough UX for personal use

**For Long-term/Polished Solution:** Option 2 (Native iOS App)

- Best user experience
- Most professional
- Can add features like offline queue, recipe preview, etc.

**For Cross-platform/Web-first:** Option 3 (PWA)

- Works on both iOS and Android
- Easier to maintain (web updates)
- Good middle ground

## Hybrid Approach

Start with Option 1 (Shortcuts) for immediate functionality, then build Option 2 (Native App) for a polished long-term solution. Option 1 remains as a fallback or for users who prefer it.

## Next Steps

1. **Immediate**: Set up iOS Shortcuts workflow (Option 1)
2. **Short-term**: Evaluate PWA Share Target API support on target devices
3. **Long-term**: Consider native iOS app if usage justifies the development effort
