# How to get your UID and Auth Key

The `UID` and `Auth Key` are unique to your camera and account. They change if you reset the camera.

## Method 1: Packet Capture (Recommended)

The easiest way to find these is to capture the network traffic of the VTech mobile app while you view the camera.

1.  **Install a Packet Capture App**:
    - **Android**: "HttpCanary" or "Packet Capture".
    - **iOS**: "Charles Proxy" or "Stream".
2.  **Start Capturing**: Open the capture app and start recording.
3.  **Open VTech App**: Open the VTech app and wait for the camera to load the live view.
4.  **Stop Capturing**: Go back to the capture app and stop.
5.  **Search**: Look for HTTP requests to a URL containing `/api/account` or `/api/devices` or similar.
    - Look for a JSON response.
    - Search inside the response body for `"uid"` (e.g., `M123456...`) and `"auth_key"` (or `authkey`, `access_token` for the p2p session).
    - The `Auth Key` is often a long alphanumeric string used for the P2P connection.

## Method 2: Python Script (If you have Client ID/Secret)

If you know the VTech API Client ID and Secret (from `vtech.py` or elsewhere), you can use a script to login and fetch the details.

```python
import requests

# You need these specific values for VTech
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
API_BASE = "https://www.vtechplanet.com" # Verify this URL

def get_creds(email, password):
    # 1. Login to get Access Token
    url = f"{API_BASE}/oauth/token"
    data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": email,
        "password": password
    }
    r = requests.post(url, data=data)
    if r.status_code != 200:
        print("Login failed:", r.text)
        return

    token = r.json().get("access_token")

    # 2. List Devices
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}/api/v1/devices", headers=headers)

    for device in r.json().get("data", []):
        print(f"Name: {device.get('nickname')}")
        print(f"UID: {device.get('uid')}")
        print(f"AuthKey: {device.get('auth_key')}")
```
