import logging
import time
import json
import os
from enum import Enum, IntEnum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import requests

try:
    import jwt  # optional (PyJWT)
except ImportError:
    jwt = None

logger = logging.getLogger(__name__)


DEFAULT_API_BASE_URL = "https://api.myiquaapp.com/v1"


class IquaSoftenerState(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"


class IquaSoftenerVolumeUnit(IntEnum):
    GALLONS = 0
    LITERS = 1


class IquaSoftenerException(Exception):
    pass


@dataclass(frozen=True)
class IquaSoftenerData:
    timestamp: datetime
    model: str
    state: IquaSoftenerState
    device_date_time: datetime
    volume_unit: IquaSoftenerVolumeUnit
    current_water_flow: float
    today_use: int
    average_daily_use: int
    total_water_available: int
    days_since_last_regeneration: int
    salt_level: int
    salt_level_percent: int
    out_of_salt_estimated_days: int
    hardness_grains: int
    water_shutoff_valve_state: int


class IquaSoftener:
    def __init__(
        self,
        username: str,
        password: str,
        device_serial_number: str,
        api_base_url: str = DEFAULT_API_BASE_URL,
    ):
        self._username: str = username
        self._password: str = password
        self._device_serial_number = device_serial_number
        self._api_base_url: str = api_base_url
        self._session: Optional[requests.Session] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._access_expires_at: Optional[int] = None
        self._device_id: Optional[str] = None  # Cache the device ID

    @property
    def device_serial_number(self) -> str:
        return self._device_serial_number

    def get_data(self) -> IquaSoftenerData:
        device_id = self._get_device_id()
        device = self._get_device_detail(device_id)
        props = device.get("properties", {})
        enriched = device.get("enriched_data", {}).get("water_treatment", {})

        def val(name: str, default=None):
            return props.get(name, {}).get("value", default)

        model_desc = val("model_description", "Unknown Model")
        model_id = val("model_id", "N/A")

        # Get device date from properties or use current time
        device_date_str = val("device_date")
        if device_date_str:
            try:
                # Parse the device date, assuming it's in ISO format
                device_date_time = datetime.fromisoformat(
                    device_date_str.rstrip("Z")
                ).replace(tzinfo=ZoneInfo("UTC"))
            except (ValueError, AttributeError):
                device_date_time = datetime.now(tz=ZoneInfo("UTC"))
        else:
            device_date_time = datetime.now(tz=ZoneInfo("UTC"))

        return IquaSoftenerData(
            timestamp=datetime.now(),
            model=f"{model_desc} ({model_id})",
            state=(
                IquaSoftenerState.ONLINE
                if val("service_active", True)
                else IquaSoftenerState.OFFLINE
            ),
            device_date_time=device_date_time,
            volume_unit=IquaSoftenerVolumeUnit(int(val("volume_unit_enum", 0))),
            current_water_flow=float(
                props.get("current_water_flow_gpm", {}).get("converted_value", 0.0)
            ),
            today_use=int(val("gallons_used_today", 0)),
            average_daily_use=int(val("avg_daily_use_gals", 0)),
            total_water_available=int(val("treated_water_avail_gals", 0)),
            days_since_last_regeneration=int(val("days_since_last_regen", 0)),
            salt_level=int(val("salt_level_tenths", 0) / 10),
            salt_level_percent=int(enriched.get("salt_level_percent", 0)),
            out_of_salt_estimated_days=int(val("out_of_salt_estimate_days", 0)),
            hardness_grains=int(val("hardness_grains", 0)),
            water_shutoff_valve_state=int(val("water_shutoff_valve", 0)),
        )

    def get_flow_and_salt(self) -> dict:
        """Return just flow (gpm) and salt level percent for quick dashboards."""
        device_id = self._get_device_id()
        device = self._get_device_detail(device_id)
        props = device.get("properties", {})
        flow = props.get("current_water_flow_gpm", {}).get("converted_value", 0.0)
        salt = (
            device.get("enriched_data", {})
            .get("water_treatment", {})
            .get("salt_level_percent")
        )
        return {"flow_gpm": flow, "salt_percent": salt}

    def set_water_shutoff_valve(self, state: int):
        if state not in (0, 1):
            raise ValueError(
                "Invalid state for water shut off valve (should be 0 or 1)."
            )

        device_id = self._get_device_id()
        url = f"/devices/{device_id}/command"

        # Convert state to action string
        action = "close" if state == 1 else "open"
        payload = {"function": "water_shutoff_valve", "action": action}

        response = self._request("PUT", url, json=payload)
        if response.status_code != 200:
            raise IquaSoftenerException(
                f"Invalid status ({response.status_code}) for set water shutoff valve request"
            )
        response_data = response.json()
        return response_data

    def open_water_shutoff_valve(self):
        """Open the water shutoff valve (allow water flow)."""
        return self.set_water_shutoff_valve(0)

    def close_water_shutoff_valve(self):
        """Close the water shutoff valve (stop water flow)."""
        return self.set_water_shutoff_valve(1)

    def schedule_regeneration(self):
        """Schedule a regeneration cycle for the water softener."""
        device_id = self._get_device_id()
        url = f"/devices/{device_id}/command"
        payload = {"function": "regenerate", "action": "schedule"}

        response = self._request("PUT", url, json=payload)
        if response.status_code != 200:
            raise IquaSoftenerException(
                f"Invalid status ({response.status_code}) for schedule regeneration request"
            )
        response_data = response.json()
        return response_data

    def cancel_scheduled_regeneration(self):
        """Cancel a scheduled regeneration cycle."""
        device_id = self._get_device_id()
        url = f"/devices/{device_id}/command"
        payload = {"function": "regenerate", "action": "cancel"}

        response = self._request("PUT", url, json=payload)
        if response.status_code != 200:
            raise IquaSoftenerException(
                f"Invalid status ({response.status_code}) for cancel regeneration request"
            )
        response_data = response.json()
        return response_data

    def regenerate_now(self):
        """Start a regeneration cycle immediately."""
        device_id = self._get_device_id()
        url = f"/devices/{device_id}/command"
        payload = {"function": "regenerate", "action": "regenerate"}

        response = self._request("PUT", url, json=payload)
        if response.status_code != 200:
            raise IquaSoftenerException(
                f"Invalid status ({response.status_code}) for regenerate now request"
            )
        response_data = response.json()
        return response_data

    def get_devices(self) -> list:
        """Get list of all devices for the authenticated user."""
        return self._get_devices()

    def get_device_id(self) -> str:
        """Get the device ID for the configured serial number."""
        return self._get_device_id()

    def save_tokens(self, path: str):
        """Save authentication tokens to a file."""
        with open(path, "w") as f:
            json.dump(
                {
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "user_id": self._user_id,
                    "_access_expires_at": self._access_expires_at,
                },
                f,
            )

    def load_tokens(self, path: str):
        """Load authentication tokens from a file."""
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            data = json.load(f)
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self._user_id = data.get("user_id")
        self._access_expires_at = data.get("_access_expires_at")

    def _get_device_id(self) -> str:
        """Get the device ID for the configured serial number."""
        if self._device_id is not None:
            return self._device_id

        # Get all devices and find the one with matching serial number
        devices = self._get_devices()
        for device in devices:
            # Check serial_number field
            device_serial = (
                device.get("properties", {}).get("serial_number", {}).get("value")
            )

            if device_serial == self._device_serial_number:
                self._device_id = device["id"]
                return self._device_id

        raise IquaSoftenerException(
            f"Device with serial number '{self._device_serial_number}' not found"
        )

    def _get_devices(self) -> list:
        """Get list of all devices for the authenticated user."""
        r = self._request("GET", "/devices")
        data = r.json()
        return data.get("data", [])

    def _ensure_session(self):
        """Ensure we have a session object."""
        if self._session is None:
            self._session = requests.Session()

    def _set_tokens(self, access_token: str, refresh_token: Optional[str]):
        """Set authentication tokens and update session headers."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        if jwt:
            try:
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                exp = decoded.get("exp")
                if exp:
                    self._access_expires_at = int(exp) - 60
            except Exception:
                self._access_expires_at = None

        self._ensure_session()
        if self._access_token:
            self._session.headers.update(
                {"Authorization": f"Bearer {self._access_token}"}
            )

    def _is_token_expired(self) -> bool:
        """Check if the current access token is expired."""
        if not self._access_token:
            return True
        if self._access_expires_at is None:
            return False
        return time.time() >= self._access_expires_at

    def _login(self) -> Dict[str, Any]:
        """Authenticate with the API and get tokens."""
        self._ensure_session()
        url = f"{self._api_base_url}/auth/login"
        payload = {"email": self._username, "password": self._password}
        try:
            r = self._session.post(url, json=payload, timeout=15)
        except requests.exceptions.RequestException as ex:
            raise IquaSoftenerException(f"Exception on login request ({ex})")

        if r.status_code == 401:
            raise IquaSoftenerException(f"Authentication error ({r.text})")
        if r.status_code != 200:
            raise IquaSoftenerException(f"Login failed: {r.status_code} {r.text}")

        data = r.json()
        self._set_tokens(data.get("access_token"), data.get("refresh_token"))
        self._user_id = data.get("user_id")
        return data

    def _refresh_token(self) -> Dict[str, Any]:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise IquaSoftenerException("No refresh token available")

        self._ensure_session()
        url = f"{self._api_base_url}/auth/refresh"
        payload = {"refresh_token": self._refresh_token}
        try:
            r = self._session.post(url, json=payload, timeout=15)
        except requests.exceptions.RequestException as ex:
            raise IquaSoftenerException(f"Exception on token refresh ({ex})")

        if r.status_code != 200:
            raise IquaSoftenerException(f"Refresh failed: {r.status_code} {r.text}")

        data = r.json()
        self._set_tokens(data.get("access_token"), data.get("refresh_token"))
        return data

    def _ensure_authenticated(self):
        """Ensure we have a valid authentication token."""
        if self._is_token_expired():
            try:
                if self._refresh_token:
                    self._refresh_token()
                else:
                    self._login()
            except IquaSoftenerException:
                self._login()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make an authenticated request to the API."""
        self._ensure_authenticated()
        self._ensure_session()

        url = (
            path
            if path.startswith("http")
            else f"{self._api_base_url.rstrip('/')}/{path.lstrip('/')}"
        )

        r = self._session.request(method, url, timeout=20, **kwargs)
        if r.status_code == 401 and self._refresh_token:
            try:
                self._refresh_token()
                r = self._session.request(method, url, timeout=20, **kwargs)
            except IquaSoftenerException:
                self._login()
                r = self._session.request(method, url, timeout=20, **kwargs)

        if r.status_code != 200:
            r.raise_for_status()
        return r

    def _get_device_detail(self, device_id: str) -> dict:
        """Get detailed device information."""
        r = self._request("GET", f"/devices/{device_id}/detail-or-summary")
        data = r.json()
        return data.get("device", {})
