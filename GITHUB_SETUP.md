# GitHub Setup Guide

## ✅ Security Check Complete

Your repository has been prepared for GitHub with **NO personal data** included:

### Protected Files (Excluded via .gitignore):
- ❌ `.env` - Contains your actual API keys and secrets
- ❌ `app.db` - Contains your user data and credentials
- ❌ `*.db`, `*.sqlite` - Any database files
- ❌ `venv/` - Python virtual environment
- ❌ `.DS_Store` - macOS system files

### Safe Files (Included in repository):
- ✅ `.env.example` - Template with placeholder values
- ✅ All source code files
- ✅ Documentation (README, setup guides)
- ✅ Docker configuration
- ✅ Database migrations (schema only, no data)

---

## Push to GitHub

### Option 1: Using GitHub CLI (Recommended)

If you have GitHub CLI installed:

```bash
# Create a new GitHub repository
gh repo create tesla-amber-sync --public --source=. --remote=origin --push

# Or for private repository:
gh repo create tesla-amber-sync --private --source=. --remote=origin --push
```

### Option 2: Using GitHub Web Interface

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `tesla-amber-sync`
   - Description: "Synchronize Tesla Powerwall with Amber Electric dynamic pricing"
   - Choose Public or Private
   - **DO NOT** initialize with README (we already have one)
   - Click "Create repository"

2. **Push your code:**
   ```bash
   # Add the GitHub remote (replace YOUR_USERNAME with your GitHub username)
   git remote add origin https://github.com/YOUR_USERNAME/tesla-amber-sync.git

   # Push to GitHub
   git push -u origin main
   ```

---

## Verify Security

After pushing, verify no sensitive data was uploaded:

1. Visit your GitHub repository
2. Check that `.env` is NOT visible in the file list
3. Check that `app.db` is NOT visible
4. Verify `.env.example` IS present with placeholder values

---

## Clone and Deploy on Another Machine

When deploying elsewhere:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tesla-amber-sync.git
cd tesla-amber-sync

# Create .env from template
cp .env.example .env

# Edit .env with your actual credentials
nano .env

# Start with Docker
docker-compose up -d
```

---

## Update README

After creating the GitHub repository, update the clone URL in README.md:

Find line 73 and replace:
```bash
git clone https://github.com/YOUR_USERNAME/tesla-amber-sync.git
```

With your actual GitHub username:
```bash
git clone https://github.com/your-actual-username/tesla-amber-sync.git
```

Then commit and push the change:
```bash
git add README.md
git commit -m "Update clone URL with actual GitHub username"
git push
```

---

## Next Steps

1. ✅ Create GitHub repository (see above)
2. ✅ Push code to GitHub
3. ✅ Verify security (check .env is not visible)
4. ✅ Update README with your GitHub username
5. ✅ Test Docker deployment on clean machine
6. ✅ Add GitHub topics: `tesla`, `powerwall`, `amber-electric`, `python`, `docker`, `flask`
7. ✅ Add GitHub description
8. ✅ Consider adding a GitHub Actions workflow for CI/CD

---

## Continuous Updates

When you make changes:

```bash
# Check what changed
git status

# Add changed files
git add .

# Commit
git commit -m "Description of your changes"

# Push to GitHub
git push
```

**Remember:** Never manually add `.env` or `app.db` to git!

---

## Security Reminders

🔒 **What's Protected:**
- Your Tesla API credentials
- Your Amber Electric API token
- Your Fernet encryption key
- Your user database
- Any user passwords or API tokens

✅ **What's Safe to Share:**
- All source code
- Documentation
- Docker configuration
- Database schema (migrations)
- Example environment file

If you accidentally commit sensitive data, see:
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
