import sys
import time
import struct
import argparse
import signal
import json
import os

# Ensure we can import from root if needed
sys.path.append('/')

import vtech_stream_codes as vtech

# Mock iotc for demonstration if not installed
try:
    import iotc
    from iotc import IOTC_Initialize2, IOTC_DeInitialize, IOTC_Connect_ByUID_Parallel, IOTC_Connect_ByUID, avClientStart, avSendIOCtrl, avRecvFrameData2, avInitialize, avDeInitialize, IOTC_Set_Log_Attr, IOTC_Get_SessionID, TUTK_SDK_Set_Region
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
    def IOTC_Get_SessionID(): return -1
    def TUTK_SDK_Set_Region(region_code): return 0

STATE_FILE = "/data/bridge_state.json"

STRATEGIES = [
    {"region": 0, "method": "sequential", "name": "Global / Sequential"},
    {"region": 3, "method": "sequential", "name": "US (Wyze) / Sequential"},
    {"region": 1, "method": "sequential", "name": "Region 1 / Sequential"},
    {"region": 2, "method": "sequential", "name": "Region 2 / Sequential"},
    {"region": 4, "method": "sequential", "name": "Region 4 / Sequential"},
    {"region": 0, "method": "parallel", "name": "Global / Parallel"},
    {"region": 3, "method": "parallel", "name": "US (Wyze) / Parallel"},
]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"index": 0, "status": "new"}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description="VTech Baby Monitor Bridge to RTSP/Stdout")
    parser.add_argument("--uid", required=True, help="Camera UID")
    parser.add_argument("--auth_key", required=True, help="Camera Auth Key")
    args = parser.parse_args()

    uid = args.uid
    auth_key = args.auth_key 
    
    # --- SMART STRATEGY SELECTION ---
    state = load_state()
    idx = state.get("index", 0)
    
    # If last run crashed (status is "pending"), increment strategy
    if state.get("status") == "pending":
        print(f"Previous strategy {idx} failed/crashed. Trying next...", file=sys.stderr)
        idx = (idx + 1) % len(STRATEGIES)
        state["index"] = idx
    
    # Limit bounds
    if idx >= len(STRATEGIES):
        idx = 0
        state["index"] = 0

    current_strategy = STRATEGIES[idx]
    print(f"--- STRATEGY {idx+1}/{len(STRATEGIES)}: {current_strategy['name']} ---", file=sys.stderr)
    
    # Persist pending state
    state["status"] = "pending"
    save_state(state)
    
    # Apply Settings
    region = current_strategy["region"]
    method = current_strategy["method"]
    
    print(f"Connecting to {uid}...", file=sys.stderr)
    
    # 0. Enable Logging
    try:
        IOTC_Set_Log_Attr(255, "/var/log/iotc_native.log")
        print("Enabled IOTC native logging to /var/log/iotc_native.log", file=sys.stderr)
    except Exception as e:
        print(f"Failed to set log attr: {e}", file=sys.stderr)

    # 0.5 Set Region
    try:
        TUTK_SDK_Set_Region(region)
        print(f"Set Region: {region}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to set region: {e}", file=sys.stderr)

    # 1. Initialize IOTC
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
    sid = -1
    
    if method == "parallel":
        print(f"Trying IOTC_Connect_ByUID_Parallel...", file=sys.stderr)
        try:
            # Parallel requires a pre-allocated Session ID
            sid_pre = IOTC_Get_SessionID()
            if sid_pre < 0:
                print(f"Failed to get Session ID: {sid_pre}", file=sys.stderr)
            else:
                signal.alarm(10) # 10s timeout
                sid_ret = IOTC_Connect_ByUID_Parallel(uid, sid_pre)
                signal.alarm(0)
                
                if sid_ret < 0:
                    print(f"IOTC_Connect_ByUID_Parallel failed: {sid_ret}", file=sys.stderr)
                    sid = -1
                else:
                    sid = sid_ret
        except TimeoutError:
            print("IOTC_Connect_ByUID_Parallel timed out.", file=sys.stderr)
            sid = -1
        except Exception as e:
            print(f"IOTC_Connect_ByUID_Parallel error: {e}", file=sys.stderr)
            sid = -1
            signal.alarm(0)
            
    else: # sequential
        print(f"Trying IOTC_Connect_ByUID (Sequential)...", file=sys.stderr)
        for i in range(3):
            try:
                signal.alarm(10)
                sid = IOTC_Connect_ByUID(uid)
                signal.alarm(0)
            except TimeoutError:
                    print(f"IOTC_Connect_ByUID attempt {i+1} timed out.", file=sys.stderr)
                    sid = -1
            except Exception as e:
                    print(f"IOTC_Connect_ByUID error: {e}", file=sys.stderr)
                    sid = -1
            
            if sid >= 0:
                break
            print(f"IOTC_Connect_ByUID failed ({sid}). Retrying ({i+1}/3)...", file=sys.stderr)
            time.sleep(1)
    
    if sid < 0:
        print(f"Failed to connect to device. Error code: {sid}", file=sys.stderr)
        # We don't mark success, so next run will try next strategy
        time.sleep(5)
        sys.exit(1)

    print(f"Connected. SID: {sid}", file=sys.stderr)
    
    # IF WE REACH HERE, STRATEGY WORKED!
    state["status"] = "connected"
    save_state(state)

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
