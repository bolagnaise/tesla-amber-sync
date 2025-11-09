# Tesla Fleet API Setup Guide

This guide will walk you through setting up Tesla Fleet API credentials for the Tesla Sync application.

## Prerequisites

- A Tesla account with at least one vehicle or energy product (Powerwall/Solar)
- A publicly accessible domain with HTTPS (required for production)
- For testing: Can use `localhost` but with limited functionality

## Step 1: Create Tesla Developer Account

1. **Go to Tesla Developer Portal**
   - Visit: https://developer.tesla.com/
   - Click "Sign In" in the top right corner

2. **Sign in with your Tesla Account**
   - Use the same email/password you use for the Tesla mobile app
   - Complete any two-factor authentication if enabled

3. **Accept Developer Terms**
   - Review and accept the Tesla Developer Terms of Service
   - You'll be redirected to the Developer Dashboard

## Step 2: Register Your Application

1. **Navigate to "Apps"**
   - In the Tesla Developer Dashboard, click on "Apps" in the left sidebar
   - Click "Create Application" or "Register Application"

2. **Fill in Application Details**

   **Application Name:**
   ```
   Tesla Sync
   ```
   (Or any name you prefer - this is what users see during OAuth)

   **Description:**
   ```
   Synchronize Tesla Powerwall with Amber Electric pricing for optimized energy management
   ```

   **Purpose:**
   - Select: "Energy Management" or "Personal Use"

## Step 3: Configure OAuth Settings

### For Production (Public Domain)

**Allowed Origins:**
```
https://yourdomain.com
```

**Redirect URIs:**
```
https://yourdomain.com/tesla-fleet/callback
```

**Example:**
If your domain is `tesla-sync.example.com`:
- Allowed Origins: `https://tesla-sync.example.com`
- Redirect URI: `https://tesla-sync.example.com/tesla-fleet/callback`

### For Development/Testing (Localhost)

**Allowed Origins:**
```
http://localhost:5001
```

**Redirect URIs:**
```
http://localhost:5001/tesla-fleet/callback
```

⚠️ **Important Notes:**
- Tesla requires HTTPS for production use
- Localhost testing has limitations (virtual keys won't work fully)
- You may need to update these settings when moving from dev to production

## Step 4: Get Your Credentials

After registering your application, Tesla will provide:

1. **Client ID**
   - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (UUID format)
   - Example: `8870f845-b446-4045-9161-f810eccf282b`

2. **Client Secret**
   - Format: `ta-secret.xxxxxxxxxxxxx`
   - Example: `ta-secret.o&eQEo7a*c_AzbgG`
   - **⚠️ KEEP THIS SECRET** - Never commit to version control

3. **Save these credentials** - you'll need them for the next step

## Step 5: Configure Your Application

1. **Edit your `.env` file:**

```bash
# Tesla Fleet API Credentials
TESLA_CLIENT_ID=your-actual-client-id-here
TESLA_CLIENT_SECRET=your-actual-client-secret-here
TESLA_REDIRECT_URI=https://yourdomain.com/tesla-fleet/callback
APP_DOMAIN=https://yourdomain.com
```

2. **For localhost testing:**

```bash
# Tesla Fleet API Credentials (Development)
TESLA_CLIENT_ID=your-actual-client-id-here
TESLA_CLIENT_SECRET=your-actual-client-secret-here
TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback
APP_DOMAIN=http://localhost:5001
```

## Step 6: Required Scopes

Your application needs these OAuth scopes:

- `openid` - Basic authentication
- `email` - User email access
- `offline_access` - Refresh tokens for long-term access
- `vehicle_device_data` - Read vehicle data
- `vehicle_cmds` - Send commands to vehicles
- `vehicle_charging_cmds` - Control charging
- `energy_device_data` - Read Powerwall/Solar data
- `energy_cmds` - Control Powerwall/Solar

These are automatically requested in the `/tesla-fleet/connect` route.

## Step 7: Virtual Key Setup

### Understanding Virtual Keys

Virtual keys are required for sending commands to vehicles. They use elliptic curve cryptography (prime256v1) for security.

**The Process:**
1. App generates EC key pair (private + public)
2. Public key hosted at `/.well-known/appspecific/com.tesla.3p.public-key.pem`
3. Tesla validates the public key is accessible
4. You add the key to your vehicle via Tesla mobile app

### Public Key Hosting Requirements

Tesla requires the public key be accessible at:
```
https://yourdomain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

**For Production:**
- Must be HTTPS
- Must be publicly accessible (not behind auth)
- Must return `Content-Type: application/x-pem-file`

**For Localhost Testing:**
- The endpoint exists at `http://localhost:5001/.well-known/appspecific/com.tesla.3p.public-key.pem`
- ⚠️ Tesla cannot verify localhost keys externally
- Limited functionality - OAuth works, but vehicle pairing may fail

## Step 8: Testing Your Setup

1. **Restart the Flask application:**
   ```bash
   flask run
   ```

2. **Navigate to Dashboard:**
   - Go to http://localhost:5001 (or your domain)
   - Log in to your account

3. **Generate Virtual Keys:**
   - Find the "Tesla Fleet API" section
   - Click "Generate Keys"
   - You should see status change to "Keys Ready"

4. **Connect to Tesla:**
   - Click "Connect to Tesla"
   - You'll be redirected to Tesla's login page
   - Authorize the requested scopes
   - You'll be redirected back to your app

5. **Verify Connection:**
   - Dashboard should show "Connected" status
   - Check the Tesla Status API endpoint works

## Step 9: Pair Vehicles (Production Only)

After successful OAuth connection:

1. **Get the pairing URL:**
   - Format: `https://tesla.com/_ak/yourdomain.com`
   - The app provides this automatically

2. **On your mobile device:**
   - Tap the "Open Tesla App" button in the dashboard
   - Or manually open: `https://tesla.com/_ak/yourdomain.com`
   - This opens the Tesla mobile app

3. **In the Tesla App:**
   - You'll see a prompt to add a virtual key
   - Tap "Add Key" or "Approve"
   - Select which vehicle(s) to pair

4. **Key Permissions:**
   - The virtual key allows the app to send commands
   - You can revoke access anytime via the Tesla app (Locks screen)

## Troubleshooting

### Common Issues

**"Invalid Client ID"**
- Double-check your Client ID matches exactly
- Ensure no extra spaces or quotes
- Verify the app is active in Tesla Developer Portal

**"Redirect URI Mismatch"**
- The redirect URI in `.env` must EXACTLY match what's registered in Tesla Developer Portal
- Check for http vs https
- Check for trailing slashes
- Check port numbers

**"Public key not found" (404)**
- Ensure you've clicked "Generate Keys" first
- Check the endpoint: `http://localhost:5001/.well-known/appspecific/com.tesla.3p.public-key.pem`
- Should return a PEM-formatted public key

**"Failed to register partner account"**
- This can happen if:
  - Domain is not publicly accessible (localhost)
  - Public key endpoint returns 404
  - HTTPS certificate is invalid
- Check app logs for detailed error messages

**Virtual key pairing fails:**
- Requires HTTPS and public domain
- Won't work with localhost
- Ensure public key is accessible at `/.well-known/appspecific/com.tesla.3p.public-key.pem`
- Try the pairing URL in a browser first to verify it works

### Debug Mode

Enable detailed logging:

```python
# In your app
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Flask logs for:
- OAuth redirect URLs
- Token exchange responses
- Public key requests
- API call results

## Production Deployment

### HTTPS Setup

You need a valid SSL certificate. Options:

1. **Let's Encrypt** (Free)
   ```bash
   certbot certonly --standalone -d yourdomain.com
   ```

2. **Cloudflare** (Free)
   - Use Cloudflare as your DNS provider
   - Enable SSL (Full or Full Strict mode)

3. **Reverse Proxy (Recommended)**
   - Use nginx with Let's Encrypt
   - Example nginx config:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;

       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

       location / {
           proxy_pass http://localhost:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       # Ensure public key endpoint is accessible
       location /.well-known/appspecific/com.tesla.3p.public-key.pem {
           proxy_pass http://localhost:5001/.well-known/appspecific/com.tesla.3p.public-key.pem;
           add_header Content-Type application/x-pem-file;
       }
   }
   ```

### Update Environment Variables

```bash
# Production .env
TESLA_CLIENT_ID=your-actual-client-id
TESLA_CLIENT_SECRET=your-actual-client-secret
TESLA_REDIRECT_URI=https://yourdomain.com/tesla-fleet/callback
APP_DOMAIN=https://yourdomain.com
```

### Update Tesla Developer Portal

Change your app's settings from localhost to your production domain:
- Allowed Origins: `https://yourdomain.com`
- Redirect URIs: `https://yourdomain.com/tesla-fleet/callback`

## Security Best Practices

1. **Never commit credentials:**
   - Add `.env` to `.gitignore`
   - Use environment variables for all secrets

2. **Protect private keys:**
   - Private keys are encrypted in the database
   - Never expose them via API endpoints

3. **Rotate credentials:**
   - Regenerate Client Secret periodically
   - Use "Reset Keys" if keys are compromised

4. **Monitor access:**
   - Check Tesla app regularly for active virtual keys
   - Revoke unused keys

## Support Resources

- **Tesla Developer Documentation:** https://developer.tesla.com/docs/fleet-api
- **Tesla Fleet API Reference:** https://developer.tesla.com/docs/fleet-api/endpoints
- **Virtual Keys Guide:** https://developer.tesla.com/docs/fleet-api/virtual-keys
- **Tesla Developer Forums:** https://github.com/teslamotors/vehicle-command/discussions

## Next Steps

Once setup is complete:

1. ✅ Configure Amber Electric API token
2. ✅ Set your Tesla Energy Site ID
3. ✅ Test API connectivity
4. ✅ Set up automatic TOU schedule syncing

Your Tesla Sync integration should now be fully functional!
