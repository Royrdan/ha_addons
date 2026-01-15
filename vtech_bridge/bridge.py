import sys
import time
import struct
import argparse

# Ensure we can import from root if needed
sys.path.append('/')

import vtech_stream_codes as vtech

# Mock iotc for demonstration if not installed
try:
    import iotc
    from iotc import IOTC_Initialize2, IOTC_DeInitialize, IOTC_Connect_ByUID_Parallel, avClientStart, avSendIOCtrl, avRecvFrameData2
except ImportError:
    print("CRITICAL ERROR: 'iotc' library not found.", file=sys.stderr)
    print("You MUST provide the 'iotc' python library or 'tutk-iotc' package.", file=sys.stderr)
    print("If you have the .so/.dll and python wrapper, ensure they are in the container.", file=sys.stderr)
    
    # Define mocks so the script structure is visible, but exit early if run
    def IOTC_Initialize2(port): return 0
    def IOTC_DeInitialize(): return 0
    def IOTC_Connect_ByUID_Parallel(uid, sid): return -1
    def avClientStart(sid, user, pwd, timeout, serv_type, channel): return -1
    def avSendIOCtrl(av_index, type, payload): pass
    def avRecvFrameData2(av_index, buf, size, out_buf_size, out_frame_size, out_frame_info, frame_idx, key_frame): return -1

def main():
    parser = argparse.ArgumentParser(description="VTech Baby Monitor Bridge to RTSP/Stdout")
    parser.add_argument("--uid", required=True, help="Camera UID")
    parser.add_argument("--auth_key", required=True, help="Camera Auth Key")
    args = parser.parse_args()

    uid = args.uid
    auth_key = args.auth_key 
    
    print(f"Connecting to {uid}...", file=sys.stderr)
    
    # 1. Initialize IOTC (Platform dependent, often requires 0 or a specific port)
    init_ret = IOTC_Initialize2(0)
    if init_ret < 0:
        print(f"Failed to initialize IOTC. Error code: {init_ret}", file=sys.stderr)
        sys.exit(1)

    # 2. Connect to Device
    sid = IOTC_Connect_ByUID_Parallel(uid, 0)
    if sid < 0:
        print(f"Failed to connect to device. Error code: {sid}", file=sys.stderr)
        # Prevent tight loop restart by sleeping
        time.sleep(5)
        sys.exit(1)

    print(f"Connected. SID: {sid}", file=sys.stderr)

    # 3. Start AV Client
    # Channel 0 is standard. 
    # Account/Password is often "admin" and the AuthKey, or just AuthKey.
    av_index = avClientStart(sid, "admin", auth_key, 30, 0, 0)
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
        IOTC_DeInitialize()

if __name__ == "__main__":
    main()
