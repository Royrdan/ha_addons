#!/usr/bin/with-contenv bashio

echo "Starting VTech Bridge Add-on..."

# Read config from Home Assistant options
UID=$(bashio::config 'uid')
AUTH_KEY=$(bashio::config 'auth_key')

if [ -z "$UID" ] || [ -z "$AUTH_KEY" ]; then
    bashio::log.error "UID or Auth Key is missing! Please configure the add-on."
    exit 1
fi

echo "Configuring go2rtc..."
# Create go2rtc config
cat > /tmp/go2rtc.yaml <<EOF
streams:
  baby_monitor: exec:python3 -u /bridge.py --uid "$UID" --auth_key "$AUTH_KEY"
  
api:
  listen: ":1984"

rtsp:
  listen: ":8554"
EOF

echo "Starting go2rtc..."
go2rtc -c /tmp/go2rtc.yaml
