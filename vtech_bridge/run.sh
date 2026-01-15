#!/usr/bin/with-contenv bashio

echo "Starting VTech Bridge Add-on..."

# Diagnostic Checks
echo "--- DIAGNOSTICS ---"
python3 --version
echo "Checking IOTC library..."
python3 -c "import importlib.util; print('IOTC Library: Found' if importlib.util.find_spec('iotc') else 'IOTC Library: MISSING')"
echo "Listing root directory:"
ls -la /
echo "-------------------"

# Read config from Home Assistant options
CAMERA_UID=$(bashio::config 'uid')
AUTH_KEY=$(bashio::config 'auth_key')

if [ -z "$CAMERA_UID" ] || [ -z "$AUTH_KEY" ]; then
    bashio::log.error "UID or Auth Key is missing! Please configure the add-on."
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
go2rtc -config /tmp/go2rtc.yaml
