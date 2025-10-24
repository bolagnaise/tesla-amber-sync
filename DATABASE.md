# Database Persistence Guide

## Understanding Database Storage

Tesla-Amber-Sync uses SQLite to store:
- User accounts and encrypted credentials
- Tesla and Amber API tokens
- Configuration settings
- Price history

## Docker Database Location

### Inside Container
- Path: `/app/data/app.db`
- Created automatically on first run

### On Host (Unraid/Your Server)
- Path: `./data/app.db` (relative to docker-compose.yml location)
- **Example**: If docker-compose.yml is in `/mnt/user/appdata/tesla-amber-sync/`, then database is at `/mnt/user/appdata/tesla-amber-sync/data/app.db`

## ⚠️ Common Issue: Lost Data After Upgrade

### Why It Happens
When you run `docker-compose down && docker-compose up -d --build`, the container is recreated, but:
- ✅ If `./data` directory exists → Database is preserved
- ❌ If `./data` directory is missing → Fresh database is created
- ❌ If you run docker-compose from wrong directory → New empty database

### How to Prevent Data Loss

**Before upgrading, always ensure the data directory exists:**

```bash
# SSH into your server
ssh root@192.168.1.100

# Navigate to your app directory
cd /path/to/tesla-amber-sync

# Create data directory if it doesn't exist
mkdir -p data

# Verify it exists
ls -la data/

# Now upgrade safely
git pull
docker-compose down
docker-compose up -d --build
```

## Backup Your Database

### Manual Backup

```bash
# SSH into your server
ssh root@192.168.1.100

# Backup database
cd /path/to/tesla-amber-sync
cp data/app.db data/app.db.backup-$(date +%Y%m%d-%H%M%S)

# List backups
ls -lh data/*.backup*
```

### Automated Backup Script

Create a cron job to backup daily:

```bash
# Create backup script
cat > /path/to/tesla-amber-sync/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/path/to/tesla-amber-sync/data"
DATE=$(date +%Y%m%d-%H%M%S)
cp "$BACKUP_DIR/app.db" "$BACKUP_DIR/app.db.backup-$DATE"
# Keep only last 7 backups
ls -t "$BACKUP_DIR"/app.db.backup-* | tail -n +8 | xargs rm -f
echo "Database backed up: app.db.backup-$DATE"
EOF

chmod +x /path/to/tesla-amber-sync/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
0 2 * * * /path/to/tesla-amber-sync/backup-db.sh
```

## Restore From Backup

```bash
# SSH into your server
ssh root@192.168.1.100

# Stop container
cd /path/to/tesla-amber-sync
docker-compose down

# Restore backup
cp data/app.db.backup-YYYYMMDD-HHMMSS data/app.db

# Start container
docker-compose up -d
```

## If You Lost Your Database

### Option 1: Create New User (Fastest)
1. Go to http://your-server:5001/register
2. Create new account
3. Re-enter your API credentials in settings

### Option 2: Restore From Local Development Database

If you have a local `app.db` from development:

```bash
# From your Mac (adjust paths as needed)
scp app.db root@192.168.1.100:/path/to/tesla-amber-sync/data/app.db

# Then restart container on Unraid
ssh root@192.168.1.100
cd /path/to/tesla-amber-sync
docker-compose restart
```

## Verify Database Persistence

After any upgrade, check that your database was preserved:

```bash
# SSH into server
ssh root@192.168.1.100

# Check database exists and has content
cd /path/to/tesla-amber-sync
ls -lh data/app.db

# View users in database
docker exec tesla-amber-sync sqlite3 /app/data/app.db "SELECT email FROM user;"
```

## Unraid-Specific Notes

### Recommended Volume Path

For Unraid, use an absolute path to ensure persistence across Docker updates:

```yaml
volumes:
  - /mnt/user/appdata/tesla-amber-sync/data:/app/data
```

### Community Applications

If installing via Unraid Community Applications:
1. Set **AppData Path** to `/mnt/user/appdata/tesla-amber-sync`
2. Database will automatically persist at `/mnt/user/appdata/tesla-amber-sync/data/app.db`
3. Survives all container updates

## Troubleshooting

### Database is read-only
```bash
# Fix permissions
docker exec tesla-amber-sync chown -R root:root /app/data
docker exec tesla-amber-sync chmod 644 /app/data/app.db
```

### Database is locked
```bash
# Check for zombie processes
docker exec tesla-amber-sync ps aux | grep gunicorn

# Restart container
docker-compose restart
```

### Fresh database every restart
```bash
# Check volume mount is working
docker inspect tesla-amber-sync | grep -A 10 Mounts

# Verify ./data directory exists on host
ls -la ./data

# Create it if missing
mkdir -p ./data
docker-compose restart
```

## Migration Notes

When upgrading between versions, Flask-Migrate automatically runs database migrations via the entrypoint script (`docker-entrypoint.sh`). Your data is preserved during migrations.

If a migration fails, check logs:
```bash
docker logs tesla-amber-sync | grep -i migration
```
