# 🌍 IP Geolocation Tool

A simple, practical IP geolocation utility built following Jeremy Howard's iterative coding approach. This tool provides both CLI and API interfaces for looking up IP address location data.

## ✨ Features

- **🔍 IP Geolocation**: Get detailed location information for any IP address
- **🌐 Current IP Detection**: Automatically detect and geolocate your current IP
- **📋 CLI Interface**: User-friendly command-line interface with colored output
- **🔌 JSON API**: Clean JSON output for integration with other tools
- **⚡ Fast & Lightweight**: Minimal dependencies, quick execution
- **🛡️ Error Handling**: Robust error handling for network issues

## 🚀 Quick Start

### Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   # Using uv (recommended)
   uv pip install requests click

   # Or using pip
   pip install requests click
   ```

### Usage

#### CLI Mode (Human-Readable)

```bash
# Get your current IP location
uv run python ip_geolocate.py

# Geolocate a specific IP
uv run python ip_geolocate.py --ip 8.8.8.8

# Force current IP detection
uv run python ip_geolocate.py --current

# Show help
uv run python ip_geolocate.py --help
```

#### API Mode (JSON Output)

```bash
# Get current IP as JSON
uv run python ip_geolocate.py --json

# Get specific IP as JSON
uv run python ip_geolocate.py --ip 8.8.8.8 --json
```

#### Programmatic Usage

```python
import ip_geolocate as ig

# Get current IP address
current_ip = ig.get_current_ip()
print(f"Current IP: {current_ip}")

# Geolocate any IP address
result = ig.geolocate_ip("8.8.8.8")
print(f"Location: {result['city']}, {result['country']}")
print(f"ISP: {result['isp']}")
```

## 📊 Sample Output

### CLI Output
```
Getting current IP address...
Current IP: 99.76.168.105
Geolocating IP: 99.76.168.105
🌍 Location: Alpharetta, Georgia, United States
📡 ISP: AT&T Enterprises, LLC
⏰ Timezone: America/New_York
📍 Coordinates: 34.024, -84.2396
```

### JSON API Output
```json
{
  "ip": "8.8.8.8",
  "success": true,
  "country": "United States",
  "country_code": "US",
  "region": "Virginia",
  "city": "Ashburn",
  "zip_code": "20149",
  "latitude": 39.03,
  "longitude": -77.5,
  "timezone": "America/New_York",
  "isp": "Google LLC",
  "organization": "Google Public DNS",
  "asn": "AS15169 Google LLC"
}
```

## 🏗️ Project Structure

```
email_provision_tools/
├── ip_geolocate.py      # Main geolocation tool (CLI + API)
├── get_ip_and_lookup.py # Original prototype script
├── ai_docs/             # Documentation and credentials
│   └── creds.md
└── README.md           # This file
```

## 🔧 Dependencies

- **requests**: HTTP library for API calls
- **click**: Command-line interface framework

## 🌐 API Services Used

- **ipify.org**: For detecting current public IP address
- **ip-api.com**: For IP geolocation data (free tier: 45 requests/minute)

## 💡 Use Cases

### Email Provision Tools Integration
```python
# Example integration with email provisioning
import ip_geolocate as ig

def provision_email_for_region():
    current_ip = ig.get_current_ip()
    location = ig.geolocate_ip(current_ip)

    if location['country_code'] == 'US':
        # Provision US email service
        return setup_us_email_service()
    else:
        # Provision international service
        return setup_intl_email_service()
```

### Network Diagnostics
```bash
# Check multiple IPs for network issues
uv run python ip_geolocate.py --ip 8.8.8.8
uv run python ip_geolocate.py --ip 1.1.1.1
uv run python ip_geolocate.py --ip 208.67.222.222
```

## 🛠️ Development

### Philosophy
Built following Jeremy Howard's practical approach:
1. **Start simple** - Core functionality first
2. **Iterate quickly** - Add features incrementally
3. **Focus on utility** - Solve real problems
4. **Keep it clean** - Readable, maintainable code

### Adding Features
The modular design makes it easy to extend:

```python
# Add new data source
def geolocate_ip_extended(ip_address: str):
    base_data = geolocate_ip(ip_address)
    # Add weather, currency, or other data
    return {**base_data, "weather": get_weather(base_data["city"])}

# Add bulk processing
def geolocate_multiple_ips(ip_list: List[str]) -> List[Dict]:
    return [geolocate_ip(ip) for ip in ip_list]
```

## 🔒 Privacy & Security

- No personal data collection or storage
- All API calls are outbound only
- IP addresses are processed temporarily for geolocation
- No tracking or analytics

## 🚨 Rate Limits

- **ipify.org**: No strict limits (used for current IP only)
- **ip-api.com**: 45 requests per minute (sufficient for most use cases)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - feel free to use in your projects!

---

**Built with ❤️ for practical IP geolocation needs**
