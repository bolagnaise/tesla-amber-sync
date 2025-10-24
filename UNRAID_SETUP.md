<div align="center">
  <img src="https://raw.githubusercontent.com/bolagnaise/tesla-amber-sync/main/assets/images/logo.png" alt="Tesla-Amber-Sync Logo" width="400"/>

  # Tesla-Amber-Sync on Unraid

  Complete guide to deploy Tesla-Amber-Sync on Unraid using Docker.
</div>

## Method 1: Pre-built Docker Image (Recommended)

The easiest way to deploy is using the official pre-built image from Docker Hub.

### Quick Start with Docker Hub Image

**Option A: Using docker-compose.hub.yml**

1. SSH into your Unraid server:
```bash
ssh root@your-unraid-ip

# Create directory
mkdir -p /mnt/user/appdata/tesla-amber-sync
cd /mnt/user/appdata/tesla-amber-sync
```

2. Download the docker-compose file:
```bash
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-amber-sync/main/docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-amber-sync/main/.env.example
mv .env.example .env
```

3. Configure environment:
```bash
nano .env
```

Add your Tesla credentials (see Configuration section below).
**Note:** Encryption key is auto-generated on first run - no manual setup needed!

4. Create data directory:
```bash
mkdir -p /mnt/user/appdata/tesla-amber-sync/data
```

5. Start the container:
```bash
docker-compose -f docker-compose.hub.yml up -d
```

**Option B: Using docker run**

```bash
# Create data directory first
mkdir -p /mnt/user/appdata/tesla-amber-sync/data

docker run -d \
  --name tesla-amber-sync \
  -p 5001:5001 \
  -v /mnt/user/appdata/tesla-amber-sync/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  --restart unless-stopped \
  bolagnaise/tesla-amber-sync:latest

# Note: Encryption key is auto-generated and saved to /mnt/user/appdata/tesla-amber-sync/data/.fernet_key
# Tesla OAuth credentials can be configured via the Environment Settings page in the web UI
```

**Option C: Unraid Docker Template**

1. Go to **Docker** tab in Unraid
2. Click **Add Container**
3. Fill in settings:

| Setting | Value |
|---------|-------|
| **Name** | `tesla-amber-sync` |
| **Repository** | `bolagnaise/tesla-amber-sync:latest` |
| **Network Type** | `bridge` |
| **Port** | `5001:5001` (TCP) |
| **Path** | `/mnt/user/appdata/tesla-amber-sync/data` → `/app/data` |
| **Restart Policy** | `Unless Stopped` |

Add environment variables (see Configuration section below).

---

## Method 2: Docker Compose (Build from Source)

### Prerequisites
- Unraid 6.9.0 or later
- Docker Compose Manager plugin installed from Community Applications

### Step 1: Install Docker Compose Manager

1. Go to **Apps** tab in Unraid
2. Search for "Docker Compose Manager"
3. Click **Install**

### Step 2: Create Project Directory

SSH into your Unraid server:

```bash
ssh root@your-unraid-ip

# Create directory for the project
mkdir -p /mnt/user/appdata/tesla-amber-sync
cd /mnt/user/appdata/tesla-amber-sync
```

### Step 3: Download Docker Compose Files

```bash
# Clone the repository
git clone https://github.com/bolagnaise/tesla-amber-sync.git .

# Or manually download files using wget/curl
```

### Step 4: Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required variables in `.env`:**
```bash
# Generate a random secret key
SECRET_KEY=your-long-random-secret-key-here

# Encryption key is AUTO-GENERATED on first run (no manual setup needed!)
# Only set this if migrating from another instance with existing encrypted data
# FERNET_ENCRYPTION_KEY=your-existing-key-here

# Tesla Developer Credentials (OPTIONAL - can be configured via web UI)
# These can be set via the Environment Settings page in the web interface
# Or you can set them here for convenience
# TESLA_CLIENT_ID=your-tesla-client-id
# TESLA_CLIENT_SECRET=ta-secret.your-secret
# TESLA_REDIRECT_URI=http://your-unraid-ip:5001/tesla-fleet/callback
# APP_DOMAIN=http://your-unraid-ip:5001
```

**✨ New: Auto-Generated Encryption Key**
- The app automatically generates an encryption key on first startup
- Saved to: `/mnt/user/appdata/tesla-amber-sync/data/.fernet_key`
- Persists across container restarts via volume mount
- **Important:** Always backup this file along with your database!

### Step 5: Update docker-compose.yml for Unraid

The existing `docker-compose.yml` works, but update the volume path:

```yaml
volumes:
  - /mnt/user/appdata/tesla-amber-sync/data:/app/data
```

### Step 6: Start the Container

```bash
# Start the container
docker-compose up -d

# Check logs
docker-compose logs -f

# Access the app
# http://your-unraid-ip:5001
```

---

## Configuration

### Network Access

- **Local Access:** `http://UNRAID-IP:5001`
- **External Access:** Configure reverse proxy (nginx/swag)

### Reverse Proxy (Optional but Recommended for Fleet API)

If using Tesla Fleet API (requires HTTPS), set up a reverse proxy:

**Using Nginx Proxy Manager (Community App):**

1. Install "Nginx Proxy Manager" from Apps
2. Add proxy host:
   - **Domain:** `tesla-sync.yourdomain.com`
   - **Forward to:** `UNRAID-IP:5001`
   - **Enable SSL:** Yes (Let's Encrypt)

3. Update `.env`:
   ```bash
   TESLA_REDIRECT_URI=https://tesla-sync.yourdomain.com/tesla-fleet/callback
   APP_DOMAIN=https://tesla-sync.yourdomain.com
   ```

### Using Teslemetry (Easier for Unraid)

If you don't want to deal with HTTPS/domains, use Teslemetry:

1. Sign up at https://teslemetry.com
2. Connect your Tesla account
3. Get your API key
4. Enter it in the Settings page (no need for TESLA_CLIENT_ID/SECRET)

---

## Maintenance

### View Logs
```bash
docker logs tesla-amber-sync

# Or with Docker Compose
docker-compose logs -f
```

### Restart Container
```bash
docker restart tesla-amber-sync

# Or with Docker Compose
docker-compose restart
```

### Update to Latest Version

**If using Pre-built Image (Method 1):**
```bash
# Pull latest image
docker pull bolagnaise/tesla-amber-sync:latest

# Restart container
docker restart tesla-amber-sync

# Or with docker-compose
cd /mnt/user/appdata/tesla-amber-sync
docker-compose -f docker-compose.hub.yml pull
docker-compose -f docker-compose.hub.yml up -d
```

**If building from source (Method 2):**
```bash
cd /mnt/user/appdata/tesla-amber-sync
git pull
docker-compose down
docker-compose up -d --build
```

### Backup Database and Encryption Key

**⚠️ IMPORTANT:** Always backup both the database AND encryption key together!

```bash
# Backup both database and encryption key
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=/mnt/user/backups/tesla-amber-sync
mkdir -p $BACKUP_DIR

# Copy database
cp /mnt/user/appdata/tesla-amber-sync/data/app.db $BACKUP_DIR/app.db.backup-$DATE

# Copy encryption key (critical - without this, encrypted credentials are lost!)
cp /mnt/user/appdata/tesla-amber-sync/data/.fernet_key $BACKUP_DIR/.fernet_key.backup-$DATE

echo "Backup complete: $DATE"
```

**Why backup the encryption key?**
- The encryption key is needed to decrypt your stored API credentials
- Without it, you'll need to re-enter all your Tesla and Amber Electric credentials
- The key and database must be from the same backup to work together

---

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs tesla-amber-sync
```

Common issues:
- Missing environment variables
- Port 5001 already in use
- Permissions on `/mnt/user/appdata/tesla-amber-sync/data`

### Can't Access Web Interface

1. Check container is running: `docker ps`
2. Check port mapping: `docker port tesla-amber-sync`
3. Try accessing via: `http://UNRAID-SERVER-IP:5001`
4. Check Unraid firewall settings

### Database Permissions

If you get database errors:
```bash
chown -R nobody:users /mnt/user/appdata/tesla-amber-sync/data
chmod -R 775 /mnt/user/appdata/tesla-amber-sync/data
```

### ⚠️ User Account Lost After Container Update

**Problem:** You register/login successfully, but after rebuilding the container (`docker-compose up -d --build` or `git pull`), you can't login and need to register again.

**Cause:** The database is not being persisted across container rebuilds. This happens when:
- The volume mount path is relative (`./data`) instead of absolute
- The `data` directory doesn't exist on the host
- You're running docker-compose from a different directory

**Solution:**

1. **Check if your database is being saved:**
```bash
# SSH into Unraid
ssh root@your-unraid-ip

# Check if database exists on the host
ls -lh /mnt/user/appdata/tesla-amber-sync/data/app.db

# If it doesn't exist or is empty, that's the problem
```

2. **Fix the volume mount:**
```bash
# Stop the container
docker-compose down

# Make sure you're in the right directory
cd /mnt/user/appdata/tesla-amber-sync

# Create the data directory if it doesn't exist
mkdir -p /mnt/user/appdata/tesla-amber-sync/data

# If using docker-compose, use the Unraid-specific file:
docker-compose -f docker-compose.unraid.yml up -d --build

# Or edit your docker-compose.yml to use absolute path:
# volumes:
#   - /mnt/user/appdata/tesla-amber-sync/data:/app/data
```

3. **Verify the volume is mounted correctly:**
```bash
# Check the container's volume mounts
docker inspect tesla-amber-sync | grep -A 10 Mounts

# You should see:
# "Source": "/mnt/user/appdata/tesla-amber-sync/data"
# "Destination": "/app/data"
```

4. **Test persistence:**
```bash
# Register a new user in the web interface
# Then check the database was created on the host:
ls -lh /mnt/user/appdata/tesla-amber-sync/data/app.db

# Rebuild the container
docker-compose down && docker-compose up -d --build

# Try logging in - it should work!
```

**Using the Unraid-Specific Docker Compose File:**

For Unraid, always use `docker-compose.unraid.yml` which has the correct absolute path:

```bash
cd /mnt/user/appdata/tesla-amber-sync
docker-compose -f docker-compose.unraid.yml up -d
```

---

## Auto-Start on Unraid Boot

Docker containers in Unraid auto-start by default. To verify:

1. Go to **Docker** tab
2. Find `tesla-amber-sync`
3. Check **Autostart** is enabled

Or with Docker Compose, ensure restart policy:
```yaml
restart: unless-stopped
```

---

## Security Recommendations

1. **Use HTTPS** if exposing to internet
2. **Strong passwords** for admin account
3. **Firewall rules** - only open port 5001 locally
4. **Regular backups** of database
5. **Keep updated** - `git pull` regularly

---

## Unraid-Specific Tips

### Add to Unraid Dashboard

Create a custom icon:
1. Download logo to `/boot/config/plugins/dynamix/tesla-amber-sync.png`
2. Edit container settings
3. Set **Icon URL:** `/boot/config/plugins/dynamix/tesla-amber-sync.png`

### Monitor Resources

Check container stats:
```bash
docker stats tesla-amber-sync
```

### Integration with Unraid Notifications

Set up Unraid User Scripts to notify on sync failures.

---

## Support

- **GitHub Issues:** https://github.com/bolagnaise/tesla-amber-sync/issues
- **Unraid Forums:** Post in Docker Containers section
- **Documentation:** See main README.md

---

## Quick Reference

**Access App:** `http://UNRAID-IP:5001`

**Config Location:** `/mnt/user/appdata/tesla-amber-sync/`

**Database:** `/mnt/user/appdata/tesla-amber-sync/data/app.db`

**Logs:** `docker logs tesla-amber-sync`

**Restart:** `docker restart tesla-amber-sync`

**Update (Pre-built):** `docker pull bolagnaise/tesla-amber-sync:latest && docker restart tesla-amber-sync`

**Update (Source):** `cd /mnt/user/appdata/tesla-amber-sync && git pull && docker-compose up -d --build`

**Docker Hub:** `https://hub.docker.com/r/bolagnaise/tesla-amber-sync`
