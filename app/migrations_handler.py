# app/migrations_handler.py
"""
Application version tracking and migration handler.
Handles upgrades between versions, including SECRET_KEY changes.
"""
import os
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Version file locations
VERSION_FILE = Path(__file__).parent.parent / 'data' / '.app_version'
SECRET_KEY_HASH_FILE = Path(__file__).parent.parent / 'data' / '.secret_key_hash'

# Current application version
CURRENT_VERSION = '1.1.0'  # Updated with auto-generated keys feature


def get_secret_key_hash(secret_key):
    """Generate a hash of the SECRET_KEY for comparison."""
    return hashlib.sha256(secret_key.encode()).hexdigest()


def read_file_if_exists(filepath):
    """Read file contents if it exists, otherwise return None."""
    try:
        if filepath.exists():
            with open(filepath, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
    return None


def write_file(filepath, content):
    """Write content to file, creating parent directories if needed."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error writing to {filepath}: {e}")
        return False


def detect_secret_key_change(secret_key):
    """
    Detect if SECRET_KEY has changed since last run.

    Returns:
        bool: True if SECRET_KEY has changed, False otherwise
    """
    current_hash = get_secret_key_hash(secret_key)
    stored_hash = read_file_if_exists(SECRET_KEY_HASH_FILE)

    if stored_hash is None:
        # First run or hash file doesn't exist
        logger.info("No SECRET_KEY hash found - this appears to be first run or upgrade")
        write_file(SECRET_KEY_HASH_FILE, current_hash)
        return True  # Treat as changed to trigger migration

    if stored_hash != current_hash:
        logger.warning("⚠️  SECRET_KEY has changed! This will invalidate all user sessions.")
        logger.warning("⚠️  Users will need to log in again with their existing passwords.")
        write_file(SECRET_KEY_HASH_FILE, current_hash)
        return True

    return False


def detect_version_upgrade():
    """
    Detect if the application version has changed.

    Returns:
        tuple: (bool, str, str) - (is_upgrade, old_version, new_version)
    """
    stored_version = read_file_if_exists(VERSION_FILE)

    if stored_version is None:
        logger.info(f"No version file found - treating as new installation (version {CURRENT_VERSION})")
        write_file(VERSION_FILE, CURRENT_VERSION)
        return (True, None, CURRENT_VERSION)

    if stored_version != CURRENT_VERSION:
        logger.info(f"Version upgrade detected: {stored_version} -> {CURRENT_VERSION}")
        write_file(VERSION_FILE, CURRENT_VERSION)
        return (True, stored_version, CURRENT_VERSION)

    return (False, stored_version, CURRENT_VERSION)


def run_migrations(app, secret_key):
    """
    Run all necessary migrations on application startup.

    Args:
        app: Flask application instance
        secret_key: Current SECRET_KEY
    """
    logger.info("=" * 60)
    logger.info("Running migration checks...")
    logger.info("=" * 60)

    # Check for version upgrade
    is_upgrade, old_version, new_version = detect_version_upgrade()

    # Check for SECRET_KEY change
    secret_key_changed = detect_secret_key_change(secret_key)

    # Handle migrations
    if secret_key_changed:
        logger.warning("🔑 SECRET_KEY CHANGE DETECTED")
        logger.warning("=" * 60)
        logger.warning("All user sessions have been invalidated due to SECRET_KEY change.")
        logger.warning("Users will see 'CSRF token invalid' errors until they:")
        logger.warning("  1. Clear browser cookies for this site")
        logger.warning("  2. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)")
        logger.warning("  3. Log in again with their existing password")
        logger.warning("=" * 60)

        # Run SECRET_KEY change migrations
        migrate_secret_key_change(app)

    if is_upgrade:
        if old_version is None:
            logger.info(f"✓ New installation detected (version {new_version})")
        else:
            logger.info(f"✓ Upgraded from {old_version} to {new_version}")
            # Run version-specific migrations
            run_version_migrations(app, old_version, new_version)
    else:
        logger.info(f"✓ No version changes (current: {new_version})")

    logger.info("=" * 60)
    logger.info("Migration checks completed")
    logger.info("=" * 60)


def migrate_secret_key_change(app):
    """
    Handle SECRET_KEY change migration.

    When SECRET_KEY changes:
    - All Flask sessions become invalid (automatic)
    - CSRF tokens fail validation (automatic)
    - We just need to log the change and inform users
    """
    # Note: We don't need to manually invalidate sessions because
    # Flask can't decrypt sessions encrypted with the old SECRET_KEY.
    # They'll be automatically treated as invalid.

    logger.info("Running SECRET_KEY change migration...")
    logger.info("  - Old sessions will be automatically invalidated")
    logger.info("  - Users will need to clear cookies and log in again")
    logger.info("✓ SECRET_KEY migration complete")


def run_version_migrations(app, old_version, new_version):
    """
    Run version-specific migrations.

    Args:
        app: Flask application instance
        old_version: Previous version string
        new_version: Current version string
    """
    logger.info(f"Running version-specific migrations from {old_version} to {new_version}...")

    # Add version-specific migrations here
    # Example:
    # if old_version < '1.1.0' and new_version >= '1.1.0':
    #     migrate_to_1_1_0(app)

    # For now, just log
    logger.info("  - No version-specific database migrations needed")
    logger.info("✓ Version migration complete")


def show_migration_banner():
    """Display a helpful banner on first run after SECRET_KEY change."""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                   🔑 SECRET_KEY UPDATED                        ║
    ╠════════════════════════════════════════════════════════════════╣
    ║                                                                ║
    ║  Your SECRET_KEY has been auto-generated or changed.           ║
    ║                                                                ║
    ║  If you see "CSRF token invalid" errors when logging in:       ║
    ║    1. Clear your browser cookies for this site                 ║
    ║    2. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)              ║
    ║    3. Log in again with your existing password                 ║
    ║                                                                ║
    ║  Your data and credentials are safe - only sessions were       ║
    ║  invalidated for security.                                     ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    return banner
