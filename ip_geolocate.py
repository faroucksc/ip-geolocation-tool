#!/usr/bin/env python3
"""
IP Geolocation Tool - Simple JSON API with CLI interface
Following Jeremy Howard's iterative, practical approach
"""
import requests
import json
import sys
from typing import Optional, Dict, Any


def get_current_ip() -> Optional[str]:
    """Get current public IP address"""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        return response.json()["ip"]
    except Exception:
        return None


def geolocate_ip(ip_address: str) -> Dict[str, Any]:
    """
    Get geolocation data for an IP address
    Returns JSON-serializable dictionary
    """
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=10)
        data = response.json()

        # Return clean, structured data
        return {
            "ip": ip_address,
            "success": data.get("status") == "success",
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "region": data.get("regionName"),
            "city": data.get("city"),
            "zip_code": data.get("zip"),
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
            "timezone": data.get("timezone"),
            "isp": data.get("isp"),
            "organization": data.get("org"),
            "asn": data.get("as"),
            "raw_data": data,  # Keep original for debugging
        }
    except Exception as e:
        return {"ip": ip_address, "success": False, "error": str(e)}


def main():
    """CLI interface"""
    import click

    @click.command()
    @click.option(
        "--ip", help="IP address to geolocate (uses current IP if not provided)"
    )
    @click.option("--json", "output_json", is_flag=True, help="Output raw JSON")
    @click.option(
        "--current", "use_current", is_flag=True, help="Force use of current IP"
    )
    def cli(ip, output_json, use_current):
        """Simple IP geolocation tool"""

        # Determine IP to use
        if use_current or not ip:
            click.echo("Getting current IP address...", err=True)
            current_ip = get_current_ip()
            if not current_ip:
                click.echo("Error: Could not determine current IP address", err=True)
                sys.exit(1)
            ip = current_ip
            click.echo(f"Current IP: {ip}", err=True)

        # Get geolocation data
        click.echo(f"Geolocating IP: {ip}", err=True)
        result = geolocate_ip(ip)

        # Output
        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                click.echo(
                    f"🌍 Location: {result['city']}, {result['region']}, {result['country']}"
                )
                click.echo(f"📡 ISP: {result['isp']}")
                click.echo(f"⏰ Timezone: {result['timezone']}")
                click.echo(
                    f"📍 Coordinates: {result['latitude']}, {result['longitude']}"
                )
            else:
                click.echo(
                    f"❌ Error: {result.get('error', 'Unknown error')}", err=True
                )
                sys.exit(1)

    cli()


if __name__ == "__main__":
    # If run as script, use CLI
    main()
elif __name__ == "ip_geolocate":
    # If imported as module, expose functions
    pass
