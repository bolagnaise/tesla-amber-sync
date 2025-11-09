# Branding Assets

This document explains how to use the Tesla Sync logo across different platforms.

## Available Assets

All assets are located in `assets/images/`:

- **logo.png** (1024x1024) - Full resolution logo
- **icon-512.png** (512x512) - Medium resolution for Docker Hub, social media
- **favicon.png** (64x64) - Small icon for web browsers
- **social-preview.png** (1280x640) - GitHub social preview image

## Setup Instructions

### 1. Flask App Favicon ✅ (Already Configured)

The favicon is automatically included in all web pages via `app/templates/base.html`.

Files:
- `app/static/favicon.png` - Browser tab icon
- `app/static/icon-512.png` - Apple touch icon

No action needed - this is already set up!

### 2. GitHub Social Preview Image

This image appears when sharing your repository on social media.

**Steps:**

1. Go to your repository: https://github.com/bolagnaise/tesla-sync
2. Click **Settings** (repository settings, not account settings)
3. Scroll down to **Social preview** section
4. Click **Edit**
5. Upload `assets/images/social-preview.png`
6. Click **Save**

Your repo will now show the logo when shared on Twitter, Slack, Discord, etc.

### 3. Docker Hub Repository Icon

This icon appears next to your container image on Docker Hub.

**Steps:**

1. Go to Docker Hub: https://hub.docker.com/r/bolagnaise/tesla-sync
2. Log in to your Docker Hub account
3. Navigate to your repository page
4. Click the **Settings** tab
5. Under **Repository logo**, click **Choose file**
6. Upload `assets/images/icon-512.png`
7. Click **Update** to save

Your Docker image will now display the logo in:
- Docker Hub search results
- Repository page
- Pull commands page
- Docker Desktop

## Logo Usage Guidelines

### Colors

- **Blue**: Electric/Tesla theme (`#00A0E3`)
- **Amber/Orange**: Amber Electric theme (`#FF9500`)
- **Dark Background**: Navy/charcoal (`#1a1f2e`)

### Placement

- Always use on dark backgrounds for best contrast
- Maintain aspect ratio (don't stretch)
- Minimum size: 64x64 pixels for clarity

### What the Logo Represents

- **Tesla "T"** - Tesla Powerwall integration
- **Heartbeat waveform** - Real-time synchronization
- **Power plug** - Energy/charging
- **Blue to amber gradient** - Connection between Tesla (blue) and Amber Electric (orange)

## File Sizes

- `logo.png`: 1.2 MB (high quality, use for print/large displays)
- `icon-512.png`: 309 KB (recommended for most web uses)
- `favicon.png`: 7.7 KB (optimized for browser tabs)
- `social-preview.png`: 924 KB (optimized for social media)
