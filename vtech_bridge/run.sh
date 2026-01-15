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
    SDK_KEY=$(jq -r '.sdk_key // empty' $CONFIG_PATH)
else
    echo "Warning: /data/options.json not found. Using environment variables if available."
    CAMERA_UID=${CAMERA_UID}
    AUTH_KEY=${AUTH_KEY}
    SDK_KEY=${SDK_KEY}
fi

# Export SDK_KEY if found
if [ -n "$SDK_KEY" ]; then
    export SDK_KEY="$SDK_KEY"
fi

if [ -z "$CAMERA_UID" ] || [ -z "$AUTH_KEY" ]; then
    echo "ERROR: UID or Auth Key is missing! Please configure the add-on."
    exit 1
fi

echo "Configuring go2rtc..."

# Create debug wrapper
cat > /debug_wrapper.sh <<'EOF'
#!/bin/bash
echo "$(date): Starting bridge with args: $@" >> /var/log/bridge.err
exec python3 -u /bridge.py "$@" 2>> /var/log/bridge.err
EOF
chmod +x /debug_wrapper.sh

# Create debug log
touch /var/log/bridge.err
touch /var/log/iotc_native.log
tail -F /var/log/bridge.err /var/log/iotc_native.log &

# Create go2rtc config
cat > /tmp/go2rtc.yaml <<EOF
streams:
  baby_monitor: exec:/debug_wrapper.sh --uid "$CAMERA_UID" --auth_key "$AUTH_KEY"
  
api:
  listen: ":1984"

rtsp:
  listen: ":8554"
EOF

echo "Starting go2rtc..."
exec go2rtc -config /tmp/go2rtc.yaml
