# app/utils.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os
import secrets
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Path to store the auto-generated Fernet key
FERNET_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', '.fernet_key')

def get_or_create_fernet_key():
    """
    Get the Fernet encryption key from environment variable or auto-generate it.

    Priority:
    1. FERNET_ENCRYPTION_KEY environment variable (backward compatibility)
    2. Auto-generated key stored in /app/data/.fernet_key
    3. Generate new key and save to file

    Returns:
        bytes: The Fernet encryption key
    """
    # Check environment variable first (backward compatibility)
    env_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    if env_key:
        logger.info("Using FERNET_ENCRYPTION_KEY from environment variable")
        return env_key.encode()

    # Check if auto-generated key file exists
    if os.path.exists(FERNET_KEY_FILE):
        try:
            with open(FERNET_KEY_FILE, 'rb') as f:
                key = f.read()
            logger.info(f"Loaded Fernet key from {FERNET_KEY_FILE}")
            return key
        except Exception as e:
            logger.error(f"Error reading Fernet key file: {e}")
            raise

    # Generate new key and save it
    logger.warning("⚠️  No Fernet key found - generating new encryption key")
    logger.warning(f"⚠️  Key will be saved to: {FERNET_KEY_FILE}")
    logger.warning("⚠️  IMPORTANT: Back up this file! Without it, you cannot decrypt stored credentials.")

    key = Fernet.generate_key()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(FERNET_KEY_FILE), exist_ok=True)

    # Save key to file
    try:
        with open(FERNET_KEY_FILE, 'wb') as f:
            f.write(key)
        # Set restrictive permissions (owner read/write only)
        os.chmod(FERNET_KEY_FILE, 0o600)
        logger.info(f"✓ Fernet key generated and saved to {FERNET_KEY_FILE}")
        logger.info("✓ File permissions set to 600 (owner read/write only)")
    except Exception as e:
        logger.error(f"Error saving Fernet key to file: {e}")
        raise

    return key

# Initialize the Fernet cipher suite with auto-generated or provided key
FERNET_KEY = get_or_create_fernet_key()
cipher_suite = Fernet(FERNET_KEY)
logger.info("Encryption cipher suite initialized")

def encrypt_token(token: str) -> bytes:
    if not token:
        logger.debug("Encrypt: No token provided, returning None")
        return None
    try:
        encrypted = cipher_suite.encrypt(token.encode())
        logger.debug(f"Successfully encrypted token (length: {len(token)} -> {len(encrypted)} bytes)")
        return encrypted
    except Exception as e:
        logger.error(f"Error encrypting token: {e}")
        raise

def decrypt_token(encrypted_token: bytes) -> str:
    if not encrypted_token:
        logger.debug("Decrypt: No encrypted token provided, returning None")
        return None
    try:
        decrypted = cipher_suite.decrypt(encrypted_token).decode()
        logger.debug(f"Successfully decrypted token (encrypted length: {len(encrypted_token)} bytes -> decrypted length: {len(decrypted)})")
        return decrypted
    except Exception as e:
        logger.error(f"Error decrypting token: {e}")
        raise


def generate_tesla_key_pair():
    """
    Generate an EC key pair for Tesla Fleet API virtual keys
    Uses prime256v1 (secp256r1) curve as required by Tesla
    Returns tuple of (private_key_pem, public_key_pem) as strings
    """
    logger.info("Generating Tesla Fleet API key pair (prime256v1 curve)")

    # Generate private key using secp256r1 (prime256v1) curve
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Get public key from private key
    public_key = private_key.public_key()

    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    logger.info("Successfully generated Tesla Fleet API key pair")
    return private_pem, public_pem


def get_or_create_secret_key():
    """
    Get Flask SECRET_KEY from environment variable or auto-generate it.
    If missing, generates a secure random key and writes it to .env file.

    Returns:
        str: The SECRET_KEY
    """
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_file = os.path.join(basedir, '.env')

    # Check environment variable first
    secret_key = os.environ.get('SECRET_KEY')

    # If no key exists or it's the default dev key, generate a new one
    if not secret_key or secret_key == 'dev-secret-key-please-change-in-production':
        logger.warning("⚠️  No SECRET_KEY found - generating new key")

        # Generate a secure random key
        secret_key = secrets.token_hex(32)

        # Update .env file
        try:
            # Read existing .env content if it exists
            env_content = []
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    env_content = f.readlines()

            # Remove any existing SECRET_KEY line
            env_content = [line for line in env_content if not line.startswith('SECRET_KEY=')]

            # Add new SECRET_KEY
            env_content.append(f'SECRET_KEY={secret_key}\n')

            # Write back to .env
            with open(env_file, 'w') as f:
                f.writelines(env_content)

            # Set restrictive permissions
            os.chmod(env_file, 0o600)

            logger.info(f"✓ SECRET_KEY generated and saved to {env_file}")
            logger.info("⚠️  IMPORTANT: Back up your .env file! Without it, all user sessions will be invalidated.")

            # Update environment variable for current process
            os.environ['SECRET_KEY'] = secret_key

        except Exception as e:
            logger.error(f"Error writing SECRET_KEY to .env: {e}")
            logger.warning("Using generated key for this session only (not persisted)")

    return secret_key


def get_security_keys_info():
    """
    Get information about current security keys for display in settings.

    Returns:
        dict: Dictionary with key information
    """
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Get SECRET_KEY
    secret_key = os.environ.get('SECRET_KEY', 'Not set')

    # Get FERNET_ENCRYPTION_KEY location
    fernet_key_source = None
    if os.environ.get('FERNET_ENCRYPTION_KEY'):
        fernet_key_source = 'Environment variable (.env)'
        fernet_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    elif os.path.exists(FERNET_KEY_FILE):
        fernet_key_source = f'File: {FERNET_KEY_FILE}'
        with open(FERNET_KEY_FILE, 'rb') as f:
            fernet_key = f.read().decode()
    else:
        fernet_key_source = 'Not found'
        fernet_key = 'Not set'

    return {
        'secret_key': secret_key,
        'secret_key_source': 'Environment variable (.env)',
        'fernet_key': fernet_key,
        'fernet_key_source': fernet_key_source,
        'env_file': os.path.join(basedir, '.env'),
        'fernet_key_file': FERNET_KEY_FILE
    }
