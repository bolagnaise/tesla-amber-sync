# app/utils.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# This key MUST match the one in your .env file
FERNET_KEY = os.environ.get('FERNET_ENCRYPTION_KEY').encode()
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
