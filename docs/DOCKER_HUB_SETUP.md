# Docker Hub Setup Guide

This guide will help you set up automated Docker image builds that publish to Docker Hub whenever you push to GitHub.

## Prerequisites

- GitHub account with this repository
- Docker Hub account (free tier works)

## Step 1: Create Docker Hub Account

If you don't have one:

1. Go to https://hub.docker.com/signup
2. Create account with username: `bolagnaise` (or your preferred username)
3. Verify your email

## Step 2: Create Docker Hub Access Token

1. Log in to https://hub.docker.com/
2. Click your **profile icon** (top right) → **Account Settings**
3. Go to **Security** → **Access Tokens**
4. Click **New Access Token**
5. Settings:
   - **Description:** `GitHub Actions - Tesla Sync`
   - **Permissions:** `Read, Write, Delete`
6. Click **Generate**
7. **COPY THE TOKEN** - you won't see it again!

## Step 3: Add Token to GitHub Secrets

1. Go to your GitHub repository: https://github.com/bolagnaise/tesla-sync
2. Click **Settings** (repository settings, not your account)
3. In left sidebar: **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add secret:
   - **Name:** `DOCKER_HUB_TOKEN`
   - **Value:** Paste the token you copied from Docker Hub
6. Click **Add secret**

## Step 4: Verify Workflow File

The GitHub Actions workflow is already configured in `.github/workflows/docker-publish.yml`

It will automatically:
- ✅ Build Docker image on every push to `main`
- ✅ Build for multiple platforms (amd64, arm64)
- ✅ Tag images properly (`latest`, version tags)
- ✅ Update Docker Hub description from README
- ✅ Use build cache for faster builds

## Step 5: Test Automated Build

Push a change to trigger the build:

```bash
# Make a small change
echo "# Test" >> README.md
git add README.md
git commit -m "Test Docker Hub automation"
git push
```

## Step 6: Monitor Build Progress

1. Go to your repository on GitHub
2. Click **Actions** tab
3. You'll see "Build and Push Docker Image" workflow running
4. Click on it to see progress
5. Build takes ~5-10 minutes first time (cached after)

## Step 7: Verify on Docker Hub

Once build completes:

1. Go to https://hub.docker.com/r/bolagnaise/tesla-sync
2. You should see your image with tags:
   - `latest` - most recent main branch
   - `main` - same as latest
   - `v1.0.0` - if you use version tags

## Using the Docker Hub Image

### On Unraid or Any Docker Host

Instead of building locally, use the pre-built image:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  web:
    image: bolagnaise/tesla-sync:latest  # Use Docker Hub image
    container_name: tesla-sync
    restart: unless-stopped
    ports:
      - "5001:5001"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FERNET_ENCRYPTION_KEY=${FERNET_ENCRYPTION_KEY}
      - TESLA_CLIENT_ID=${TESLA_CLIENT_ID}
      - TESLA_CLIENT_SECRET=${TESLA_CLIENT_SECRET}
      - TESLA_REDIRECT_URI=${TESLA_REDIRECT_URI}
      - APP_DOMAIN=${APP_DOMAIN}
    volumes:
      - ./data:/app/data
```

**Or with docker run:**
```bash
docker run -d \
  --name tesla-sync \
  -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret \
  -e FERNET_ENCRYPTION_KEY=your-key \
  -e TESLA_CLIENT_ID=your-id \
  -e TESLA_CLIENT_SECRET=your-secret \
  -e TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback \
  -e APP_DOMAIN=http://localhost:5001 \
  --restart unless-stopped \
  bolagnaise/tesla-sync:latest
```

## Automatic Updates

### Update to Latest Version

```bash
# Pull latest image
docker pull bolagnaise/tesla-sync:latest

# Recreate container
docker-compose down
docker-compose up -d

# Or with docker run
docker stop tesla-sync
docker rm tesla-sync
# Run docker run command again with latest image
```

### Use Watchtower for Auto-Updates (Unraid)

Install Watchtower to automatically update containers:

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  tesla-sync \
  --interval 3600 \
  --cleanup
```

This checks for updates every hour and auto-updates the container.

## Version Tagging (Optional)

To create versioned releases:

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

This creates additional Docker tags:
- `bolagnaise/tesla-sync:1.0.0`
- `bolagnaise/tesla-sync:1.0`
- `bolagnaise/tesla-sync:1`
- `bolagnaise/tesla-sync:latest`

## Multi-Architecture Support

The workflow builds for:
- **linux/amd64** - Standard x86_64 (most servers, Unraid)
- **linux/arm64** - ARM64 (Raspberry Pi 4, Apple Silicon, some NAS)

Docker automatically pulls the correct architecture for your system.

## Troubleshooting

### Build Fails on GitHub Actions

1. Check **Actions** tab for error logs
2. Common issues:
   - Missing `DOCKER_HUB_TOKEN` secret
   - Invalid Dockerfile syntax
   - Network timeout (retry usually works)

### Can't Pull Image

```bash
# Ensure image name is correct
docker pull bolagnaise/tesla-sync:latest

# Check if public (should be)
# Visit: https://hub.docker.com/r/bolagnaise/tesla-sync
```

### Image Size

First build may be larger (~500MB). This includes:
- Python 3.9
- All dependencies
- Application code

Subsequent builds use cache and are much faster.

## Customization

### Change Docker Hub Username

Edit `.github/workflows/docker-publish.yml`:

```yaml
env:
  DOCKER_HUB_USERNAME: your-username  # Change this
  IMAGE_NAME: tesla-sync
```

### Build on Different Branches

Add branches to workflow trigger:

```yaml
on:
  push:
    branches:
      - main
      - develop  # Add other branches
```

## Benefits of Docker Hub Automation

✅ **No local builds** - Pull pre-built images
✅ **Multi-architecture** - Works on x86 and ARM
✅ **Automatic updates** - Push to GitHub = new image
✅ **Version control** - Tag releases properly
✅ **Fast deployment** - Download vs build
✅ **Build cache** - Faster subsequent builds

## Cost

- **Docker Hub Free Tier:**
  - Unlimited public repositories
  - Unlimited pulls
  - 1 concurrent build
  - No cost for this project

## Next Steps

1. ✅ Set up Docker Hub account
2. ✅ Create access token
3. ✅ Add token to GitHub secrets
4. ✅ Push to GitHub to trigger build
5. ✅ Use image on Unraid/Docker hosts
6. ✅ Set up Watchtower for auto-updates (optional)

---

**Your image will be available at:**
`docker pull bolagnaise/tesla-sync:latest`

**Docker Hub page:**
https://hub.docker.com/r/bolagnaise/tesla-sync
