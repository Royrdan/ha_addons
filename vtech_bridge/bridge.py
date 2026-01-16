import sys
import time
import struct
import argparse
import signal
import json
import os
import multiprocessing

# Ensure we can import from root if needed
sys.path.append('/')

import vtech_stream_codes as vtech

# Mock iotc for demonstration if not installed
try:
    import iotc
    from iotc import IOTC_Initialize2, IOTC_DeInitialize, IOTC_Connect_ByUID_Parallel, IOTC_Connect_ByUID, avClientStart, avClientStartEx, avSendIOCtrl, avRecvFrameData2, avInitialize, avDeInitialize, IOTC_Set_Log_Attr, IOTC_Get_SessionID, TUTK_SDK_Set_Region, TUTK_SDK_Set_License_Key
except ImportError:
    print("CRITICAL ERROR: 'iotc' library not found.", file=sys.stderr)
    # Define mocks so the script structure is visible, but exit early if run
    def IOTC_Initialize2(port): return 0
    def IOTC_DeInitialize(): return 0
    def IOTC_Connect_ByUID_Parallel(uid, sid): return -1
    def IOTC_Connect_ByUID(uid): return -1
    def avInitialize(max_channel_num): return 0
    def avDeInitialize(): return 0
    def avClientStart(sid, user, pwd, timeout, serv_type, channel): return -1
    def avClientStartEx(sid, user, pwd, timeout, channel, resend=0, security_mode=0, auth_type=0): return -1
    def avSendIOCtrl(av_index, type, payload): pass
    def avRecvFrameData2(av_index, buf, size, out_buf_size, out_frame_size, out_frame_info, frame_idx): return -1
    def IOTC_Set_Log_Attr(log_level, path): pass
    def IOTC_Get_SessionID(): return -1
    def TUTK_SDK_Set_Region(region_code): return 0
    def TUTK_SDK_Set_License_Key(key): return 0

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

def bridge_worker(uid, auth_key, region, method, status_queue):
    """
    Runs the actual bridge logic in a separate process.
    """
    print(f"[Worker] Starting. Region={region}, Method={method}", file=sys.stderr)
    
    # 0. Enable Logging
    try:
        IOTC_Set_Log_Attr(255, "/var/log/iotc_native.log")
        print("[Worker] Enabled IOTC native logging", file=sys.stderr)
    except Exception as e:
        print(f"[Worker] Failed to set log attr: {e}", file=sys.stderr)

    # 0.5 Set Region
    try:
        TUTK_SDK_Set_Region(region)
        print(f"[Worker] Set Region: {region}", file=sys.stderr)
    except Exception as e:
        print(f"[Worker] Failed to set region: {e}", file=sys.stderr)

    # 0.6 Set License Key
    sdk_key = os.getenv("SDK_KEY") or os.getenv("TUTK_LICENSE_KEY")
    if sdk_key:
        try:
            print(f"[Worker] Setting License Key (len={len(sdk_key)})...", file=sys.stderr)
            TUTK_SDK_Set_License_Key(sdk_key)
        except Exception as e:
            print(f"[Worker] Failed to set license key: {e}", file=sys.stderr)
    else:
        print("[Worker] No SDK_KEY provided. Connection may hang if library requires it.", file=sys.stderr)

    # 1. Initialize IOTC
    init_ret = IOTC_Initialize2(0)
    if init_ret < 0:
        print(f"[Worker] Failed to initialize IOTC: {init_ret}", file=sys.stderr)
        return
    
    # Initialize AV
    av_ret = avInitialize(0)
    if av_ret < 0:
        print(f"[Worker] Failed to initialize AV: {av_ret}", file=sys.stderr)

    # 2. Connect
    sid = -1
    print(f"[Worker] Connecting...", file=sys.stderr)
    
    if method == "parallel":
        try:
            sid_pre = IOTC_Get_SessionID()
            if sid_pre < 0:
                print(f"[Worker] Failed to get Session ID: {sid_pre}", file=sys.stderr)
            else:
                sid_ret = IOTC_Connect_ByUID_Parallel(uid, sid_pre)
                if sid_ret < 0:
                    print(f"[Worker] Parallel connect failed: {sid_ret}", file=sys.stderr)
                else:
                    sid = sid_ret
        except Exception as e:
            print(f"[Worker] Parallel exception: {e}", file=sys.stderr)
    else: # sequential
        try:
            sid = IOTC_Connect_ByUID(uid)
            if sid < 0:
                print(f"[Worker] Sequential connect failed: {sid}", file=sys.stderr)
        except Exception as e:
            print(f"[Worker] Sequential exception: {e}", file=sys.stderr)

    if sid < 0:
        print("[Worker] Connection failed.", file=sys.stderr)
        return

    print(f"[Worker] Connected! SID: {sid}", file=sys.stderr)
    
    # Notify Main Process of success
    status_queue.put("CONNECTED")

    # 3. Start AV Client
    av_index = -1
    # Simple retry for AV start
    for i in range(3):
        # Try avClientStartEx with DTLS (SecurityMode=2) as VTech uses it
        print(f"[Worker] Starting AV Client (Attempt {i+1})...", file=sys.stderr)
        av_index = avClientStartEx(sid, "admin", auth_key, 30, 0, resend=0, security_mode=2, auth_type=0)
        if av_index >= 0:
            break
        print(f"[Worker] AV start failed: {av_index}. Retrying...", file=sys.stderr)
        time.sleep(1)

    if av_index < 0:
        print(f"[Worker] Failed to start AV client: {av_index}", file=sys.stderr)
        iotc.IOTC_Session_Close(sid)
        return

    print(f"[Worker] AV Client Started. AVIndex: {av_index}", file=sys.stderr)

    # 4. Start Stream
    vtech.start_stream(sid, av_index, 0)
    
    # 5. Receive Loop
    buf = bytearray(1024 * 1024) # 1MB buffer
    print("[Worker] Stream started. Outputting video...", file=sys.stderr)
    
    try:
        while True:
            out_buf_size = [0]
            out_frame_size = [0]
            out_frame_info = [0] * 10
            frame_idx = [0]
            # key_frame = [0]
            
            ret = avRecvFrameData2(av_index, buf, len(buf), out_buf_size, out_frame_size, out_frame_info, frame_idx)
            
            if ret > 0:
                frame_data = buf[:ret] 
                sys.stdout.buffer.write(frame_data)
                sys.stdout.flush()
            elif ret == -20012: # IOTC_ER_TIMEOUT
                continue
            elif ret < 0:
                print(f"[Worker] Error receiving frame: {ret}", file=sys.stderr)
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        vtech.stop_stream(sid, av_index, 0)
        iotc.avClientStop(av_index)
        iotc.IOTC_Session_Close(sid)
        avDeInitialize()
        IOTC_DeInitialize()

def main():
    parser = argparse.ArgumentParser(description="VTech Baby Monitor Bridge Smart Tester")
    parser.add_argument("--uid", required=True, help="Camera UID")
    parser.add_argument("--auth_key", required=True, help="Camera Auth Key")
    args = parser.parse_args()

    # --- SMART STRATEGY SELECTION ---
    state = load_state()
    idx = state.get("index", 0)
    
    # If last run crashed/hung (status pending), move to next
    if state.get("status") == "pending":
        print(f"Previous strategy {idx} failed. Moving to next...", file=sys.stderr)
        idx = (idx + 1) % len(STRATEGIES)
        state["index"] = idx
    
    if idx >= len(STRATEGIES):
        idx = 0
        state["index"] = 0

    current_strategy = STRATEGIES[idx]
    print(f"--- STRATEGY {idx+1}/{len(STRATEGIES)}: {current_strategy['name']} ---", file=sys.stderr)
    
    state["status"] = "pending"
    save_state(state)
    
    # Run Worker
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=bridge_worker, args=(args.uid, args.auth_key, current_strategy["region"], current_strategy["method"], queue))
    p.start()
    
    # Wait for connection success
    try:
        msg = queue.get(timeout=15) # Wait 15s for connection
        if msg == "CONNECTED":
            print("Strategy Successful! Marking state as connected.", file=sys.stderr)
            state["status"] = "connected"
            save_state(state)
            
            # Wait for worker to finish (forever)
            p.join()
            sys.exit(0)
    except multiprocessing.queues.Empty:
        print("Connection timed out (Hard Hang). Killing worker...", file=sys.stderr)
        p.terminate()
        p.join()
        sys.exit(1) # Exit to restart with next strategy
    except KeyboardInterrupt:
        p.terminate()
        sys.exit(0)
    
    # If worker exited early without success
    print("Worker exited early.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
