FROM python:3.12-slim-bookworm

# Setup base
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Go2RTC (amd64)
RUN curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_amd64 -o /usr/local/bin/go2rtc \
    && chmod +x /usr/local/bin/go2rtc

# Install Python dependencies
RUN pip3 install --no-cache-dir requests

# Copy data
COPY run.sh /
COPY bridge.py /
COPY vtech_stream_codes.py /

# Copy custom IOTC wrapper and native library
COPY iotc.py /
COPY test_libs.py /
COPY libs /libs
COPY libIOTCAPIs.so /usr/lib/
COPY libAVAPIs.so /usr/lib/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
