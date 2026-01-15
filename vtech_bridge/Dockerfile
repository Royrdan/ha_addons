# Stage 1: Get ARM64 filesystem (libs + python)
# We use a specific hash or tag to ensure consistency
FROM --platform=linux/arm64 python:3.12-slim-bookworm AS arm_base
# No RUN commands here! They would fail on x86 host without qemu.

# Stage 2: Final x86 image
FROM python:3.12-slim-bookworm

# Install QEMU static (x86 binary that runs arm64)
RUN apt-get update && apt-get install -y \
    qemu-user-static \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Go2RTC (x86 version - Native performance!)
RUN curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_i386 -o /usr/local/bin/go2rtc \
    && chmod +x /usr/local/bin/go2rtc

# Setup ARM64 Environment
WORKDIR /arm64_env
COPY --from=arm_base / /arm64_env/

# Install Python dependencies for ARM64 into the ARM environment
# We use the host (x86) pip to install into the target directory with cross-platform flags
RUN pip3 install --target /arm64_env/usr/local/lib/python3.12/site-packages \
    --platform manylinux2014_aarch64 \
    --only-binary=:all: \
    --python-version 3.12 \
    requests

# Copy Bridge Scripts & Libs
# We put them in a shared location (/app)
WORKDIR /app
COPY run.sh bridge.py vtech_stream_codes.py iotc.py test_libs.py /app/

# Copy all libs to system path (where iotc.py looks) and ARM env path
COPY *.so /usr/lib/
COPY *.so /arm64_env/usr/lib/

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]
