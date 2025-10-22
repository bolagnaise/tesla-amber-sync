# app/api_clients.py
"""API clients for Amber Electric and Tesla"""
import requests
import logging
from datetime import datetime, timedelta
from app.utils import decrypt_token
import time
import os

logger = logging.getLogger(__name__)


class AmberAPIClient:
    """Client for Amber Electric API"""

    BASE_URL = "https://api.amber.com.au/v1"

    def __init__(self, api_token):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        logger.info("AmberAPIClient initialized")

    def test_connection(self):
        """Test the API connection"""
        try:
            logger.info("Testing Amber API connection")
            response = requests.get(
                f"{self.BASE_URL}/sites",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Amber API connection successful - Status: {response.status_code}")
            return True, "Connected"
        except requests.exceptions.RequestException as e:
            logger.error(f"Amber API connection failed: {e}")
            return False, str(e)

    def get_current_prices(self, site_id=None):
        """Get current electricity prices"""
        try:
            # If no site_id provided, get the first site
            if not site_id:
                sites = self.get_sites()
                if sites:
                    site_id = sites[0]['id']
                else:
                    logger.error("No Amber sites found")
                    return None

            logger.info(f"Fetching current prices for site: {site_id}")
            response = requests.get(
                f"{self.BASE_URL}/sites/{site_id}/prices/current",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched current prices: {len(data)} channels")
            logger.debug(f"Price data: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current prices: {e}")
            return None

    def get_sites(self):
        """Get all sites associated with the account"""
        try:
            logger.info("Fetching Amber sites")
            response = requests.get(
                f"{self.BASE_URL}/sites",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            sites = response.json()
            logger.info(f"Found {len(sites)} Amber sites")
            return sites
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sites: {e}")
            return []

    def get_price_forecast(self, site_id=None, start_date=None, end_date=None, next_hours=24):
        """Get price forecast for a site"""
        try:
            # If no site_id provided, get the first site
            if not site_id:
                sites = self.get_sites()
                if sites:
                    site_id = sites[0]['id']
                else:
                    logger.error("No Amber sites found")
                    return None

            if not start_date:
                start_date = datetime.utcnow()
            if not end_date:
                end_date = start_date + timedelta(hours=next_hours)

            logger.info(f"Fetching {next_hours}h price forecast for site {site_id}")
            params = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }
            response = requests.get(
                f"{self.BASE_URL}/sites/{site_id}/prices",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched forecast: {len(data)} price points")
            logger.debug(f"Forecast data sample: {data[:2] if len(data) > 0 else 'None'}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching price forecast: {e}")
            return None


class TeslemetryAPIClient:
    """Client for Teslemetry API (Tesla API proxy service)"""

    BASE_URL = "https://api.teslemetry.com"

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info("TeslemetryAPIClient initialized")

    def test_connection(self):
        """Test the API connection"""
        try:
            logger.info("Testing Teslemetry API connection")
            response = requests.get(
                f"{self.BASE_URL}/api/1/products",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Teslemetry API connection successful - Status: {response.status_code}")
            return True, "Connected"
        except requests.exceptions.RequestException as e:
            logger.error(f"Teslemetry API connection failed: {e}")
            return False, str(e)

    def get_energy_sites(self):
        """Get all energy sites (Powerwalls, Solar)"""
        try:
            logger.info("Fetching Tesla energy sites via Teslemetry")
            response = requests.get(
                f"{self.BASE_URL}/api/1/products",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Filter for energy sites only
            energy_sites = [p for p in data.get('response', []) if 'energy_site_id' in p]
            logger.info(f"Found {len(energy_sites)} Tesla energy sites via Teslemetry")
            return energy_sites
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching energy sites via Teslemetry: {e}")
            return []

    def get_site_status(self, site_id):
        """Get status of a specific energy site"""
        try:
            # First, get the list of products to find the energy site
            logger.info(f"Getting products list to find energy site {site_id}")
            products_response = requests.get(
                f"{self.BASE_URL}/api/1/products",
                headers=self.headers,
                timeout=10
            )
            products_response.raise_for_status()
            products_data = products_response.json()
            logger.info(f"Products response: {products_data}")

            # Find the energy site in products
            energy_site = None
            for product in products_data.get('response', []):
                if product.get('energy_site_id') and str(product.get('energy_site_id')) == str(site_id):
                    energy_site = product
                    break
                # Also try resource_id field
                if product.get('resource') and str(product.get('resource')) == str(site_id):
                    energy_site = product
                    break

            if not energy_site:
                logger.error(f"Energy site {site_id} not found in products list")
                logger.error(f"Available products: {products_data}")
                return None

            logger.info(f"Found energy site in products: {energy_site}")

            # Try to get live_status using the correct endpoint
            site_id_numeric = energy_site.get('energy_site_id') or site_id
            logger.info(f"Fetching site status for {site_id_numeric} via Teslemetry")

            # Teslemetry uses /api/1/energy_sites/{id}/live_status
            response = requests.get(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id_numeric}/live_status",
                headers=self.headers,
                timeout=10
            )

            # Log response before raising
            logger.info(f"Teslemetry live_status response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Teslemetry error response: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched site status via Teslemetry")
            logger.info(f"Teslemetry response keys: {list(data.keys())}")
            logger.info(f"Full Teslemetry site status response: {data}")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching site status via Teslemetry: {e}")
            return None

    def get_site_info(self, site_id):
        """Get detailed information about a site"""
        try:
            logger.info(f"Fetching site info for {site_id} via Teslemetry")
            response = requests.get(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/site_info",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched site info via Teslemetry")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching site info via Teslemetry: {e}")
            return None

    def get_battery_level(self, site_id):
        """Get current battery level"""
        try:
            status = self.get_site_status(site_id)
            if status:
                battery_level = status.get('percentage_charged', 0)
                logger.info(f"Battery level: {battery_level}%")
                return battery_level
            return None
        except Exception as e:
            logger.error(f"Error getting battery level via Teslemetry: {e}")
            return None

    def set_operation_mode(self, site_id, mode):
        """
        Set the Powerwall operation mode

        Args:
            site_id: Energy site ID
            mode: Operation mode - 'self_consumption', 'backup', 'autonomous'
        """
        try:
            logger.info(f"Setting operation mode to {mode} for site {site_id}")
            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/operation",
                headers=self.headers,
                json={"default_real_mode": mode},
                timeout=10
            )

            logger.info(f"Set operation mode response status: {response.status_code}")
            if response.status_code not in [200, 201, 202]:
                logger.error(f"Error response: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set operation mode to {mode}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting operation mode via Teslemetry: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None

    def set_backup_reserve(self, site_id, backup_reserve_percent):
        """
        Set the backup reserve percentage

        Args:
            site_id: Energy site ID
            backup_reserve_percent: Backup reserve percentage (0-100)
        """
        try:
            logger.info(f"Setting backup reserve to {backup_reserve_percent}% for site {site_id}")
            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/backup",
                headers=self.headers,
                json={"backup_reserve_percent": backup_reserve_percent},
                timeout=10
            )

            logger.info(f"Set backup reserve response status: {response.status_code}")
            if response.status_code not in [200, 201, 202]:
                logger.error(f"Error response: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set backup reserve to {backup_reserve_percent}%")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting backup reserve via Teslemetry: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None

    def get_time_based_control_settings(self, site_id):
        """Get current time-based control settings"""
        try:
            logger.info(f"Getting time-based control settings for site {site_id}")
            response = requests.get(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched time-based control settings")
            logger.debug(f"TBC settings: {data}")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting time-based control settings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None

    def set_time_based_control_settings(self, site_id, tou_settings):
        """
        Set time-based control settings with schedule

        Args:
            site_id: Energy site ID
            tou_settings: Dictionary with TOU schedule settings
        """
        try:
            logger.info(f"Setting time-based control settings for site {site_id}")
            logger.info(f"TOU settings: {tou_settings}")

            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings",
                headers=self.headers,
                json=tou_settings,
                timeout=10
            )

            logger.info(f"Set TOU settings response status: {response.status_code}")
            if response.status_code not in [200, 201, 202]:
                logger.error(f"Error response: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set time-based control settings")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting time-based control settings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None

    def set_tariff_rate(self, site_id, tariff_content):
        """
        Set the electricity tariff/rate plan for the site

        Uses the time_of_use_settings endpoint with tariff_content_v2

        Args:
            site_id: Energy site ID
            tariff_content: Dictionary with complete tariff structure (v2 format)
        """
        try:
            logger.info(f"Setting tariff rate for site {site_id}")
            logger.debug(f"Tariff structure keys: {list(tariff_content.keys())}")

            # The payload structure for time_of_use_settings with tariff
            payload = {
                "tou_settings": {
                    "tariff_content_v2": tariff_content
                }
            }

            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings",
                headers=self.headers,
                json=payload,
                timeout=30  # Longer timeout for tariff updates
            )

            logger.info(f"Set tariff via TOU settings response status: {response.status_code}")
            if response.status_code not in [200, 201, 202]:
                logger.error(f"Error response: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set tariff rate for site {site_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting tariff rate: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None


def get_amber_client(user):
    """Get an Amber API client for the user"""
    if not user.amber_api_token_encrypted:
        logger.warning(f"No Amber token for user {user.email}")
        return None

    try:
        api_token = decrypt_token(user.amber_api_token_encrypted)
        return AmberAPIClient(api_token)
    except Exception as e:
        logger.error(f"Error creating Amber client: {e}")
        return None


class TeslaFleetAPIClient:
    """Client for Tesla Fleet API (direct OAuth with virtual keys)"""

    # Tesla Fleet API base URL for North America
    BASE_URL = "https://fleet-api.prd.na.vn.cloud.tesla.com"

    def __init__(self, access_token, refresh_token=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        logger.info("TeslaFleetAPIClient initialized")

    def test_connection(self):
        """Test the API connection"""
        try:
            logger.info("Testing Tesla Fleet API connection")
            response = requests.get(
                f"{self.BASE_URL}/api/1/products",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Tesla Fleet API connection successful - Status: {response.status_code}")
            return True, "Connected"
        except requests.exceptions.RequestException as e:
            logger.error(f"Tesla Fleet API connection failed: {e}")
            return False, str(e)

    def get_energy_sites(self):
        """Get all energy sites (Powerwalls, Solar)"""
        try:
            logger.info("Fetching Tesla energy sites via Fleet API")
            response = requests.get(
                f"{self.BASE_URL}/api/1/products",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Filter for energy sites only
            products = data.get('response', [])
            energy_sites = [p for p in products if 'energy_site_id' in p]
            logger.info(f"Found {len(energy_sites)} Tesla energy sites via Fleet API")
            return energy_sites
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching energy sites via Fleet API: {e}")
            return []

    def get_site_status(self, site_id):
        """Get status of a specific energy site"""
        try:
            logger.info(f"Fetching site status for {site_id} via Fleet API")
            response = requests.get(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/live_status",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched site status via Fleet API")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching site status via Fleet API: {e}")
            return None

    def get_site_info(self, site_id):
        """Get detailed information about a site"""
        try:
            logger.info(f"Fetching site info for {site_id} via Fleet API")
            response = requests.get(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/site_info",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched site info via Fleet API")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching site info via Fleet API: {e}")
            return None

    def get_battery_level(self, site_id):
        """Get current battery level"""
        try:
            status = self.get_site_status(site_id)
            if status:
                battery_level = status.get('percentage_charged', 0)
                logger.info(f"Battery level: {battery_level}%")
                return battery_level
            return None
        except Exception as e:
            logger.error(f"Error getting battery level via Fleet API: {e}")
            return None

    def set_operation_mode(self, site_id, mode):
        """Set the Powerwall operation mode"""
        try:
            logger.info(f"Setting operation mode to {mode} for site {site_id}")
            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/operation",
                headers=self.headers,
                json={"default_real_mode": mode},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set operation mode to {mode}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting operation mode via Fleet API: {e}")
            return None

    def set_backup_reserve(self, site_id, backup_reserve_percent):
        """Set the backup reserve percentage"""
        try:
            logger.info(f"Setting backup reserve to {backup_reserve_percent}% for site {site_id}")
            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/backup",
                headers=self.headers,
                json={"backup_reserve_percent": backup_reserve_percent},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set backup reserve to {backup_reserve_percent}%")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting backup reserve via Fleet API: {e}")
            return None

    def set_tariff_rate(self, site_id, tariff_content):
        """Set the electricity tariff/rate plan for the site"""
        try:
            logger.info(f"Setting tariff rate for site {site_id}")
            logger.debug(f"Tariff structure keys: {list(tariff_content.keys())}")

            # Format payload for Fleet API
            payload = {
                "tou_settings": {
                    "tariff_content_v2": tariff_content
                }
            }

            response = requests.post(
                f"{self.BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings",
                headers=self.headers,
                json=payload,
                timeout=30  # Longer timeout for tariff updates
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully set tariff rate for site {site_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting tariff rate via Fleet API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None


def get_tesla_client(user):
    """Get a Tesla API client for the user (Fleet API or Teslemetry fallback)"""

    # Try Tesla Fleet API first (direct OAuth)
    if user.tesla_access_token_encrypted:
        try:
            logger.info("Using TeslaFleetAPIClient (direct OAuth)")
            access_token = decrypt_token(user.tesla_access_token_encrypted)
            refresh_token = decrypt_token(user.tesla_refresh_token_encrypted) if user.tesla_refresh_token_encrypted else None
            return TeslaFleetAPIClient(access_token, refresh_token)
        except Exception as e:
            logger.error(f"Error creating Fleet API client: {e}")

    # Fallback to Teslemetry
    if user.teslemetry_api_key_encrypted:
        try:
            logger.info("Using TeslemetryAPIClient (fallback)")
            api_key = decrypt_token(user.teslemetry_api_key_encrypted)
            return TeslemetryAPIClient(api_key)
        except Exception as e:
            logger.error(f"Error creating Teslemetry client: {e}")

    logger.warning(f"No Tesla API credentials for user {user.email}")
    return None
