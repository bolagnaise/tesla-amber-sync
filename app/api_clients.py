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
        self.base_url = self.BASE_URL
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
                f"{self.base_url}/sites",
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
                f"{self.base_url}/sites/{site_id}/prices/current",
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
                f"{self.base_url}/sites",
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

    def get_price_forecast(self, site_id=None, start_date=None, end_date=None, next_hours=24, resolution=None):
        """
        Get price forecast for a site

        Args:
            site_id: Site ID (defaults to first site)
            start_date: Start date (defaults to now)
            end_date: End date (defaults to start + next_hours)
            next_hours: Hours to fetch if end_date not specified
            resolution: Interval resolution in minutes (5 or 30, defaults to billing interval)
        """
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

            res_str = f" at {resolution}min resolution" if resolution else ""
            logger.info(f"Fetching {next_hours}h price forecast{res_str} for site {site_id}")
            params = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }

            # Add resolution parameter if specified (5 or 30 minutes)
            if resolution:
                params["resolution"] = resolution

            response = requests.get(
                f"{self.base_url}/sites/{site_id}/prices",
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

    def get_usage(self, site_id=None, start_date=None, end_date=None):
        """
        Get historical usage data for a site

        Args:
            site_id: Site ID (defaults to first site)
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to now)
        """
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
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()

            logger.info(f"Fetching usage data for site {site_id}")
            params = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }

            response = requests.get(
                f"{self.base_url}/sites/{site_id}/usage",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched usage data: {len(data)} data points")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching usage data: {e}")
            return None

    def raw_api_call(self, endpoint, method='GET', params=None, json_data=None):
        """
        Make a raw API call to any Amber endpoint

        Args:
            endpoint: API endpoint path (e.g., '/sites' or '/sites/{site_id}/prices')
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            json_data: JSON body for POST/PUT requests

        Returns:
            tuple: (success: bool, data: dict or None, status_code: int)
        """
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"Making {method} request to {url}")

            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=10
            )

            # Return both success status and data
            success = response.status_code < 400
            data = None

            try:
                data = response.json()
            except:
                data = {"raw_text": response.text}

            logger.info(f"API call completed with status {response.status_code}")
            return success, data, response.status_code

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API call to {endpoint}: {e}")
            return False, {"error": str(e)}, 0


class TeslemetryAPIClient:
    """Client for Teslemetry API (Tesla API proxy service)"""

    BASE_URL = "https://api.teslemetry.com"

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = self.BASE_URL
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
                f"{self.base_url}/api/1/products",
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
                f"{self.base_url}/api/1/products",
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
                f"{self.base_url}/api/1/products",
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
                f"{self.base_url}/api/1/energy_sites/{site_id_numeric}/live_status",
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
                f"{self.base_url}/api/1/energy_sites/{site_id}/site_info",
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

    def get_current_tariff(self, site_id):
        """
        Get the current TOU tariff from Tesla Powerwall

        Returns the complete tariff structure that's currently programmed into the Powerwall.
        This can be saved and later restored.

        Returns:
            dict: Complete tariff structure or None if error
        """
        try:
            logger.info(f"Fetching current tariff for site {site_id} via Teslemetry")

            # Get site_info which includes TOU settings
            site_info = self.get_site_info(site_id)
            if not site_info:
                logger.error("Failed to fetch site info")
                return None

            # Extract the tariff from site_info
            # Teslemetry returns it as 'tariff_content_v2' (not 'utility_tariff_content_v2')
            tariff = site_info.get('tariff_content_v2')

            if tariff:
                logger.info(f"Successfully extracted current tariff: {tariff.get('name', 'Unknown')}")
                logger.debug(f"Tariff keys: {list(tariff.keys())}")
                return tariff
            else:
                logger.warning("No tariff found in site_info")
                logger.debug(f"Site info keys: {list(site_info.keys())}")
                return None

        except Exception as e:
            logger.error(f"Error getting current tariff: {e}")
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

    def get_calendar_history(self, site_id, kind='energy', period='day', end_date=None, timezone='Australia/Brisbane'):
        """
        Get historical energy data from Tesla calendar history

        Args:
            site_id: Energy site ID
            kind: 'energy' or 'power'
            period: 'day', 'week', 'month', 'year', or 'lifetime'
            end_date: End date (datetime string with timezone, e.g., '2025-10-26T23:59:59+10:00')
            timezone: IANA timezone string (e.g., 'Australia/Brisbane', 'America/New_York')

        Returns:
            dict: Calendar history data with time_series array
        """
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            # Default to current time in user's timezone if no end_date provided
            # Use 11:59 PM to avoid midnight issues
            if not end_date:
                user_tz = ZoneInfo(timezone)
                now = datetime.now(user_tz)
                # Use 23:59:59 to avoid midnight issues
                end_dt = now.replace(hour=23, minute=59, second=59)
                end_date = end_dt.isoformat()

            logger.info(f"Fetching calendar history for site {site_id} via Teslemetry: kind={kind}, period={period}, end_date={end_date}")

            params = {
                'kind': kind,
                'period': period,
                'end_date': end_date
            }

            response = requests.get(
                f"{self.base_url}/api/1/energy_sites/{site_id}/calendar_history",
                headers=self.headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched calendar history via Teslemetry")
            return data.get('response', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching calendar history via Teslemetry: {e}")
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
                f"{self.base_url}/api/1/energy_sites/{site_id}/operation",
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
                f"{self.base_url}/api/1/energy_sites/{site_id}/backup",
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
            url = f"{self.base_url}/api/1/energy_sites/{site_id}/time_of_use_settings"
            logger.info(f"Getting time-based control settings for site {site_id}")
            logger.info(f"Teslemetry API URL: {url}")
            logger.debug(f"Request headers: {dict((k,v if k != 'Authorization' else '***') for k,v in self.headers.items())}")

            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            logger.info(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Raw response text: {response.text}")

            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched time-based control settings")
            logger.debug(f"Parsed JSON response: {data}")

            # Extract response field
            result = data.get('response', {})
            logger.info(f"Returning {len(result) if result else 0} items from response field")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting time-based control settings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response status: {e.response.status_code}")
                logger.error(f"Error response text: {e.response.text}")
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
                f"{self.base_url}/api/1/energy_sites/{site_id}/time_of_use_settings",
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

            # Log a sample of the tariff being sent for debugging
            if 'energy_charges' in tariff_content and tariff_content['energy_charges']:
                energy_charges_keys = list(tariff_content['energy_charges'].keys())
                logger.debug(f"Tariff energy_charges seasons: {energy_charges_keys}")

            # Debug: Check if tou_periods are being sent
            if 'seasons' in tariff_content and 'Summer' in tariff_content['seasons']:
                if 'tou_periods' in tariff_content['seasons']['Summer']:
                    sample_period = list(tariff_content['seasons']['Summer']['tou_periods'].items())[0]
                    logger.info(f"DEBUG: Sending tou_periods - First period: {sample_period[0]} = {sample_period[1]}")
                else:
                    logger.warning(f"DEBUG: No tou_periods in tariff being sent!")

            response = requests.post(
                f"{self.base_url}/api/1/energy_sites/{site_id}/time_of_use_settings",
                headers=self.headers,
                json=payload,
                timeout=30  # Longer timeout for tariff updates
            )

            logger.info(f"Set tariff via TOU settings response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            # Log the full response to debug tariff update issues
            logger.info(f"Teslemetry API response: {data}")

            # Check if the response indicates success
            if isinstance(data, dict):
                if 'response' in data:
                    response_data = data['response']
                    if isinstance(response_data, dict) and 'result' in response_data:
                        if not response_data['result']:
                            reason = response_data.get('reason', 'Unknown reason')
                            logger.error(f"Tariff update failed: {reason}")
                            logger.error(f"Full response: {data}")
                            return None

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


class AEMOAPIClient:
    """Client for AEMO (Australian Energy Market Operator) NEM Data API

    Fetches real-time electricity pricing data from the National Electricity Market (NEM).
    No authentication required - uses public API endpoints.
    """

    BASE_URL = "https://visualisations.aemo.com.au/aemo/apps/api/report/ELEC_NEM_SUMMARY"

    # NEM Regions
    REGIONS = {
        'NSW1': 'New South Wales',
        'QLD1': 'Queensland',
        'VIC1': 'Victoria',
        'SA1': 'South Australia',
        'TAS1': 'Tasmania'
    }

    def __init__(self):
        """Initialize AEMO API client (no auth required)"""
        logger.info("AEMOAPIClient initialized")

    def get_current_prices(self):
        """Get current 5-minute dispatch prices for all NEM regions

        Returns:
            dict: Price data for all regions or None on error
            Example: {
                'NSW1': {'price': 72.06, 'timestamp': '2025-11-08T21:00:00', 'status': 'FIRM'},
                'QLD1': {'price': 69.89, 'timestamp': '2025-11-08T21:00:00', 'status': 'FIRM'},
                ...
            }
        """
        try:
            logger.info("Fetching current AEMO NEM prices")
            response = requests.get(self.BASE_URL, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Extract regional prices from the ELEC_NEM_SUMMARY data
            prices = {}

            if 'ELEC_NEM_SUMMARY' in data:
                for item in data['ELEC_NEM_SUMMARY']:
                    region = item.get('REGIONID')
                    if region in self.REGIONS:
                        prices[region] = {
                            'price': float(item.get('RRP', 0)),  # Regional Reference Price in $/MWh
                            'timestamp': item.get('SETTLEMENTDATE'),
                            'status': item.get('PRICE_STATUS', 'UNKNOWN'),
                            'demand': float(item.get('TOTALDEMAND', 0)),
                            'region_name': self.REGIONS[region]
                        }

            logger.info(f"Successfully fetched AEMO prices for {len(prices)} regions")
            logger.debug(f"AEMO price data: {prices}")
            return prices

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching AEMO prices: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing AEMO data: {e}")
            return None

    def get_region_price(self, region):
        """Get current price for a specific region

        Args:
            region: Region code (NSW1, QLD1, VIC1, SA1, TAS1)

        Returns:
            dict: Price data for the region or None
        """
        if region not in self.REGIONS:
            logger.error(f"Invalid region: {region}. Must be one of {list(self.REGIONS.keys())}")
            return None

        prices = self.get_current_prices()
        if prices:
            return prices.get(region)
        return None

    def check_price_spike(self, region, threshold_dollars_per_mwh):
        """Check if current price exceeds threshold (price spike detection)

        Args:
            region: Region code (NSW1, QLD1, VIC1, SA1, TAS1)
            threshold_dollars_per_mwh: Spike threshold in $/MWh (e.g., 300)

        Returns:
            tuple: (is_spike: bool, current_price: float, price_data: dict)
        """
        price_data = self.get_region_price(region)
        if not price_data:
            return False, None, None

        current_price = price_data['price']
        is_spike = current_price >= threshold_dollars_per_mwh

        if is_spike:
            logger.warning(f"PRICE SPIKE DETECTED in {region}: ${current_price}/MWh (threshold: ${threshold_dollars_per_mwh}/MWh)")
        else:
            logger.info(f"Normal price in {region}: ${current_price}/MWh (threshold: ${threshold_dollars_per_mwh}/MWh)")

        return is_spike, current_price, price_data


def get_tesla_client(user):
    """Get a Tesla API client for the user (Teslemetry only)"""

    if user.teslemetry_api_key_encrypted:
        try:
            logger.info("Using TeslemetryAPIClient")
            api_key = decrypt_token(user.teslemetry_api_key_encrypted)
            return TeslemetryAPIClient(api_key)
        except Exception as e:
            logger.error(f"Error creating Teslemetry client: {e}")
            return None

    logger.warning(f"No Teslemetry API key configured for user {user.email}")
    return None
