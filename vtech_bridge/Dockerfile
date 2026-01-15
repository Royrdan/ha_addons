ARG BUILD_FROM
FROM $BUILD_FROM

# Setup base
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bind-tools \
    gcompat \
    libc6-compat

# Install Go2RTC
ARG BUILD_ARCH
RUN if [ "${BUILD_ARCH}" = "aarch64" ]; then \
    curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_arm64 -o /usr/local/bin/go2rtc; \
    elif [ "${BUILD_ARCH}" = "amd64" ]; then \
    curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_amd64 -o /usr/local/bin/go2rtc; \
    elif [ "${BUILD_ARCH}" = "armv7" ]; then \
    curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_armv7 -o /usr/local/bin/go2rtc; \
    fi \
    && chmod +x /usr/local/bin/go2rtc

# Install Python dependencies
# Attempt to install a common library, but users often need to provide their own IOTC wrapper
RUN pip3 install --no-cache-dir requests --break-system-packages

# Copy data
COPY run.sh /
COPY bridge.py /
COPY vtech_stream_codes.py /

# Copy custom IOTC wrapper and native library
COPY iotc.py /
COPY libIOTCAPIs.so /usr/lib/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
