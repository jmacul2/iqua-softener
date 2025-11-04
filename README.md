# iQua Softener Python Library

A comprehensive Python library for interacting with iQua water softeners through their REST API and WebSocket interface. This library provides both basic device data retrieval and advanced real-time monitoring capabilities.

## Features

- **Device Data Retrieval** - Get comprehensive water softener status and metrics
- **Water Shutoff Valve Control** - Open/close water shutoff valves remotely
- **Regeneration Management** - Schedule, cancel, and trigger regeneration cycles
- **Real-time Data** - WebSocket support for live water flow and device status updates
- **Home Assistant Integration** - Designed for easy integration with Home Assistant
- **JWT Authentication** - Secure token-based authentication with automatic refresh
- **Device Discovery** - Automatic device ID lookup by serial number

## Installation

```bash
pip install iqua_softener
```

## Quick Start

```python
from iqua_softener import IquaSoftener

# Initialize the softener client
softener = IquaSoftener(
    username='your_email@example.com',
    password='your_password', 
    device_serial_number='your_device_serial'
)

# Get current device data
data = softener.get_data()
print(f"Current flow: {data.current_water_flow} GPM")
print(f"Salt level: {data.salt_level_percent}%")
print(f"Water available: {data.total_water_available} gallons")
```

## API Reference

### Basic Usage

#### Initialize Client

```python
softener = IquaSoftener(
    username='email@example.com',           # Your iQua account email
    password='password',                    # Your iQua account password  
    device_serial_number='ABC123',          # Device serial number
    api_base_url='https://api.myiquaapp.com/v1',  # Optional: API base URL
    enable_websocket=True,                  # Optional: Enable real-time data
    external_realtime_data=None             # Optional: For Home Assistant integration
)
```

#### Get Device Data

```python
data = softener.get_data()  # Returns IquaSoftenerData object

# Available properties:
print(data.timestamp)                      # When data was retrieved [datetime]
print(data.model)                          # Device model [str]
print(data.state)                          # Online/Offline [IquaSoftenerState]
print(data.device_date_time)               # Device timestamp [datetime]
print(data.volume_unit)                    # Gallons/Liters [IquaSoftenerVolumeUnit]
print(data.current_water_flow)             # Current flow rate [float]
print(data.today_use)                      # Water used today [int]
print(data.average_daily_use)              # Average daily usage [int]
print(data.total_water_available)          # Treated water available [int]
print(data.days_since_last_regeneration)   # Days since last regen [int]
print(data.salt_level)                     # Salt level [int]
print(data.salt_level_percent)             # Salt level percentage [int]
print(data.out_of_salt_estimated_days)     # Estimated days until empty [int]
print(data.hardness_grains)                # Water hardness [int]
print(data.water_shutoff_valve_state)      # Valve state: 1=open, 0=closed [int]
```

#### Quick Dashboard Data

```python
# Get just flow and salt level for dashboards
quick_data = softener.get_flow_and_salt()
print(f"Flow: {quick_data['flow_gpm']} GPM")
print(f"Salt: {quick_data['salt_percent']}%")
```

### Water Shutoff Valve Control

```python
# Control valve state (1 = open, 0 = closed)
softener.set_water_shutoff_valve(1)        # Open valve
softener.set_water_shutoff_valve(0)        # Close valve

# Convenience methods
softener.open_water_shutoff_valve()        # Open valve
softener.close_water_shutoff_valve()       # Close valve
```

### Regeneration Control

```python
# Schedule a regeneration cycle
softener.schedule_regeneration()

# Cancel a scheduled regeneration
softener.cancel_scheduled_regeneration()

# Start regeneration immediately
softener.regenerate_now()
```

### Real-time Data with WebSocket

```python
# Start WebSocket for real-time updates
softener.start_websocket()

# Get data with real-time flow information
data = softener.get_data()  # Now includes live flow data

# Get specific real-time property
current_flow = softener.get_realtime_property("current_water_flow_gpm")

# Stop WebSocket when done
softener.stop_websocket()
```

### Device Management

```python
# Get all devices for account
devices = softener.get_devices()

# Get device ID for current serial number
device_id = softener.get_device_id()
```

### Token Management

```python
# Save authentication tokens to file
softener.save_tokens('/path/to/tokens.json')

# Load previously saved tokens
softener.load_tokens('/path/to/tokens.json')
```

## Home Assistant Integration

The library supports integration with Home Assistant by allowing external management of WebSocket connections:

```python
# Initialize without internal WebSocket
softener = IquaSoftener(
    username="user@example.com",
    password="password", 
    device_serial_number="ABC123",
    enable_websocket=False  # Let HA manage WebSocket
)

# Get WebSocket URI for Home Assistant
ws_uri = softener.get_websocket_uri()

# In your HA integration, connect to WebSocket and update real-time data:
realtime_data = {
    "current_water_flow_gpm": {
        "value": 2.5,
        "converted_property": {"value": 2.5}
    }
}
softener.update_external_realtime_data(realtime_data)

# Now get_data() uses HA-managed real-time data
data = softener.get_data()
```

## Data Sources and Priority

The library intelligently combines data from multiple sources:

1. **Real-time WebSocket data** - Live flow and status updates
2. **Enriched API data** - Processed values like salt percentages and regeneration info  
3. **Properties API data** - Raw device properties as fallback

### Data Mapping

| Library Field | Primary Source | Fallback Source |
|---------------|----------------|-----------------|
| `current_water_flow` | WebSocket real-time | `properties.current_water_flow_gpm.converted_value` |
| `today_use` | `enriched_data.gallons_used_today` | `properties.gallons_used_today.value` |
| `total_water_available` | `enriched_data.treated_water_available.value` | `properties.treated_water_avail_gals.value` |
| `days_since_last_regeneration` | `enriched_data.days_since_last_recharge` | `properties.days_since_last_regen.value` |
| `salt_level_percent` | `enriched_data.salt_level_percent` | - |
| `water_shutoff_valve_state` | `enriched_data.water_shutoff_valve.status` | `properties.water_shutoff_valve` |

## Error Handling

```python
from iqua_softener import IquaSoftenerException

try:
    data = softener.get_data()
except IquaSoftenerException as e:
    print(f"Error: {e}")
```

## Advanced Usage

### Custom API Base URL

```python
softener = IquaSoftener(
    username="user@example.com",
    password="password",
    device_serial_number="ABC123",
    api_base_url="https://custom-api.example.com/v1"
)
```

### Disable WebSocket

```python
# For environments where WebSocket isn't needed or available
softener = IquaSoftener(
    username="user@example.com",
    password="password", 
    device_serial_number="ABC123",
    enable_websocket=False
)
```

### Manual WebSocket Management

```python
# Start WebSocket in background
softener.start_websocket()

# Check if specific real-time data is available
if softener.get_realtime_property("current_water_flow_gpm") is not None:
    print("Real-time flow data available")

# Stop WebSocket
softener.stop_websocket()
```

## Version History

### Version 2.0.0 (Current)
- **NEW**: WebSocket support for real-time data updates
- **NEW**: Water shutoff valve control methods
- **NEW**: Regeneration cycle management (schedule, cancel, trigger)
- **NEW**: Device discovery by serial number
- **NEW**: Home Assistant integration support
- **NEW**: Enriched data source prioritization
- **IMPROVED**: JWT authentication with automatic token refresh
- **IMPROVED**: Enhanced error handling and logging
- **IMPROVED**: Data source fallback strategies

### Version 1.x
- Basic device data retrieval
- Simple authentication
- Limited API coverage

## Requirements

- Python 3.7+
- `requests` - HTTP client library
- `PyJWT` - JWT token handling
- `websockets` - WebSocket client (optional, for real-time data)

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Contributing

This library was enhanced by Jay McEntire (jay.mcentire@gmail.com) based on the original work by Artur Zabroński. Contributions and improvements are welcome!