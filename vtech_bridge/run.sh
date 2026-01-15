#!/bin/bash

echo "Starting VTech Bridge Add-on..."

# Diagnostic Checks
echo "--- DIAGNOSTICS ---"
python3 --version
echo "Checking IOTC library..."
python3 /iotc.py
echo "Listing root directory:"
ls -la /
echo "-------------------"

# Read config from Home Assistant options
CONFIG_PATH="/data/options.json"

if [ -f "$CONFIG_PATH" ]; then
    CAMERA_UID=$(jq -r '.uid // empty' $CONFIG_PATH)
    AUTH_KEY=$(jq -r '.auth_key // empty' $CONFIG_PATH)
else
    echo "Warning: /data/options.json not found. Using environment variables if available."
    CAMERA_UID=${CAMERA_UID}
    AUTH_KEY=${AUTH_KEY}
fi

if [ -z "$CAMERA_UID" ] || [ -z "$AUTH_KEY" ]; then
    echo "ERROR: UID or Auth Key is missing! Please configure the add-on."
    exit 1
fi

echo "Configuring go2rtc..."
# Create go2rtc config
cat > /tmp/go2rtc.yaml <<EOF
streams:
  baby_monitor: exec:python3 -u /bridge.py --uid "$CAMERA_UID" --auth_key "$AUTH_KEY"
  
api:
  listen: ":1984"

rtsp:
  listen: ":8554"
EOF

echo "Starting go2rtc..."
exec go2rtc -config /tmp/go2rtc.yaml
