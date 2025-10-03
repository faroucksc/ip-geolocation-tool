import requests as rq
import json

# Get current IP address
try:
    current_ip_response = rq.get("https://api.ipify.org?format=json")
    current_ip_data = current_ip_response.json()
    current_ip = current_ip_data["ip"]
    print(f"Your current IP address: {current_ip}")
except Exception as e:
    print(f"Error getting current IP: {e}")
    exit(1)

# Now use your original script logic with the current IP
ip = current_ip
if ip != "q":
    try:
        req = rq.get(url=f"http://ip-api.com/json/{ip}")
        print("\nGeolocation data for your IP:")
        print(json.dumps(req.json(), indent=2))
    except Exception as e:
        print(f"Error querying IP geolocation: {e}")
else:
    print("No IP to lookup")
