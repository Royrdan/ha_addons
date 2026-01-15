import sys
import time
import struct
import argparse
import signal

# Ensure we can import from root if needed
sys.path.append('/')

import vtech_stream_codes as vtech

# Mock iotc for demonstration if not installed
try:
    import iotc
    from iotc import IOTC_Initialize2, IOTC_DeInitialize, IOTC_Connect_ByUID_Parallel, IOTC_Connect_ByUID, avClientStart, avSendIOCtrl, avRecvFrameData2, avInitialize, avDeInitialize, IOTC_Set_Log_Attr
except ImportError:
    print("CRITICAL ERROR: 'iotc' library not found.", file=sys.stderr)
    print("You MUST provide the 'iotc' python library or 'tutk-iotc' package.", file=sys.stderr)
    print("If you have the .so/.dll and python wrapper, ensure they are in the container.", file=sys.stderr)
    
    # Define mocks so the script structure is visible, but exit early if run
    def IOTC_Initialize2(port): return 0
    def IOTC_DeInitialize(): return 0
    def IOTC_Connect_ByUID_Parallel(uid, sid): return -1
    def IOTC_Connect_ByUID(uid): return -1
    def avInitialize(max_channel_num): return 0
    def avDeInitialize(): return 0
    def avClientStart(sid, user, pwd, timeout, serv_type, channel): return -1
    def avSendIOCtrl(av_index, type, payload): pass
    def avRecvFrameData2(av_index, buf, size, out_buf_size, out_frame_size, out_frame_info, frame_idx, key_frame): return -1
    def IOTC_Set_Log_Attr(log_level, path): pass

def main():
    parser = argparse.ArgumentParser(description="VTech Baby Monitor Bridge to RTSP/Stdout")
    parser.add_argument("--uid", required=True, help="Camera UID")
    parser.add_argument("--auth_key", required=True, help="Camera Auth Key")
    args = parser.parse_args()

    uid = args.uid
    auth_key = args.auth_key 
    
    print(f"Connecting to {uid}...", file=sys.stderr)
    
    # 0. Enable Logging
    try:
        # Enable verbose logging to file
        IOTC_Set_Log_Attr(255, "/var/log/iotc_native.log")
        print("Enabled IOTC native logging to /var/log/iotc_native.log", file=sys.stderr)
    except Exception as e:
        print(f"Failed to set log attr: {e}", file=sys.stderr)

    # 1. Initialize IOTC (Platform dependent, often requires 0 or a specific port)
    init_ret = IOTC_Initialize2(0)
    if init_ret < 0:
        print(f"Failed to initialize IOTC. Error code: {init_ret}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize AV
    av_ret = avInitialize(0)
    if av_ret < 0:
        print(f"Failed to initialize AV. Error code: {av_ret}", file=sys.stderr)

    # Define timeout handler
    def timeout_handler(signum, frame):
        raise TimeoutError("IOTC Connect Timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)

    # 2. Connect to Device
    print(f"Trying IOTC_Connect...", file=sys.stderr)
    sid = -1
    
    # Try Parallel First (usually more robust)
    print(f"Trying IOTC_Connect_ByUID_Parallel...", file=sys.stderr)
    try:
        signal.alarm(10) # 10s timeout
        sid = IOTC_Connect_ByUID_Parallel(uid, 0)
        signal.alarm(0)
    except TimeoutError:
        print("IOTC_Connect_ByUID_Parallel timed out.", file=sys.stderr)
        sid = -1
    except Exception as e:
        print(f"IOTC_Connect_ByUID_Parallel error: {e}", file=sys.stderr)
        sid = -1
        signal.alarm(0)

    # If Parallel failed, try sequential
    if sid < 0:
        print(f"Parallel failed ({sid}). Trying sequential IOTC_Connect_ByUID...", file=sys.stderr)
        for i in range(3):
            try:
                signal.alarm(10)
                sid = IOTC_Connect_ByUID(uid)
                signal.alarm(0)
            except TimeoutError:
                 print(f"IOTC_Connect_ByUID attempt {i+1} timed out.", file=sys.stderr)
                 sid = -1
            
            if sid >= 0:
                break
            print(f"IOTC_Connect_ByUID failed ({sid}). Retrying ({i+1}/3)...", file=sys.stderr)
            time.sleep(1)
    
    if sid < 0:
        print(f"Failed to connect to device. Error code: {sid}", file=sys.stderr)
        # Prevent tight loop restart by sleeping
        time.sleep(5)
        sys.exit(1)

    print(f"Connected. SID: {sid}", file=sys.stderr)

    # 3. Start AV Client
    # Channel 0 is standard. 
    # Account/Password is often "admin" and the AuthKey, or just AuthKey.
    av_index = -1
    for i in range(3):
        av_index = avClientStart(sid, "admin", auth_key, 30, 0, 0)
        if av_index >= 0:
            break
        print(f"avClientStart failed ({av_index}). Retrying ({i+1}/3)...", file=sys.stderr)
        time.sleep(1)

    if av_index < 0:
        print(f"Failed to start AV client. Error code: {av_index}", file=sys.stderr)
        iotc.IOTC_Session_Close(sid)
        time.sleep(5)
        sys.exit(1)

    print(f"AV Client Started. AVIndex: {av_index}", file=sys.stderr)

    # 4. Send Start Stream Command
    payload = vtech.create_start_stream_payload(0)
    vtech.start_stream(sid, av_index, 0)
    
    # 5. Receive Loop
    # Buffer for video data
    buf = bytearray(1024 * 1024) # 1MB buffer
    
    print("Stream started. Outputting raw H.264 to stdout...", file=sys.stderr)
    
    try:
        while True:
            # Mock variables for C-style pointer returns
            out_buf_size = [0]
            out_frame_size = [0]
            out_frame_info = [0] * 10 # SFrameInfo struct
            frame_idx = [0]
            key_frame = [0]
            
            ret = avRecvFrameData2(av_index, buf, len(buf), out_buf_size, out_frame_size, out_frame_info, frame_idx, key_frame)
            
            if ret > 0:
                # Success, write raw frame to stdout
                # We need to extract the exact bytes. 
                # Assuming 'ret' is the number of bytes read or 'out_frame_size[0]' is.
                frame_data = buf[:ret] 
                
                # Write binary data to stdout
                sys.stdout.buffer.write(frame_data)
                sys.stdout.flush()
                
            elif ret == -20012: # IOTC_ER_TIMEOUT
                continue
            elif ret < 0:
                print(f"Error receiving frame: {ret}", file=sys.stderr)
                break
                
    except KeyboardInterrupt:
        print("Stopping...", file=sys.stderr)
    finally:
        vtech.stop_stream(sid, av_index, 0)
        iotc.avClientStop(av_index)
        iotc.IOTC_Session_Close(sid)
        avDeInitialize()
        IOTC_DeInitialize()

if __name__ == "__main__":
    main()
