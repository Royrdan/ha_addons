# VTech Baby Monitor Bridge Home Assistant Add-on

This Add-on bridges VTech baby monitors (using TUTK IOTC P2P protocol) to a local RTSP stream that Home Assistant can consume.

## Installation

1.  Copy the `vtech_bridge` directory to your Home Assistant `/addons/` directory.
    - You should end up with `/addons/vtech_bridge/config.json`, etc.
2.  Go to **Settings > Add-ons > Add-on Store**.
3.  Click the **Refresh** button (top right dots) to detect local add-ons.
4.  Install **VTech Baby Monitor Bridge**.

## Configuration

You must provide the UID and Auth Key obtained from the VTech API.

```yaml
uid: "YOUR_DEVICE_UID"
auth_key: "YOUR_AUTH_KEY"
```

## Dependencies

**Crucial Note:** This add-on requires the `iotc` python library (or `tutk-iotc` package).

- The Dockerfile attempts to install `tutk-iotc` from PyPI.
- If this package does not work or is missing, you must provide the python wrapper and `.so`/`.dll` files.
- You can drop `iotc.py` and `libIOTCAPIs.so` into the add-on directory and uncomment the `COPY` lines in the `Dockerfile`.

## Usage

Once started, the add-on starts an internal RTSP server (using `go2rtc`).

**RTSP Stream URL:** `rtsp://<your-home-assistant-ip>:8554/vtech`

Add this to Home Assistant using the **Generic Camera** integration.
