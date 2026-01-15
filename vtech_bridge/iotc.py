import ctypes
import os
import sys

# Load IOTC Library
# Try /usr/lib first (where Dockerfile will put it)
lib_path = "/usr/lib/libIOTCAPIs.so"
if not os.path.exists(lib_path):
    # Try local
    lib_path = os.path.join(os.path.dirname(__file__), "libIOTCAPIs.so")

try:
    # Load with RTLD_GLOBAL so symbols are available to libAVAPIs
    _lib = ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
except OSError as e:
    print(f"Failed to load library {lib_path}: {e}", file=sys.stderr)
    raise

# Load AV Library
av_lib_path = "/usr/lib/libAVAPIs.so"
if not os.path.exists(av_lib_path):
    av_lib_path = os.path.join(os.path.dirname(__file__), "libAVAPIs.so")

try:
    _av_lib = ctypes.CDLL(av_lib_path)
except OSError as e:
    print(f"Failed to load AV library {av_lib_path}: {e}", file=sys.stderr)
    raise

# Define constants
IOTC_ER_TIMEOUT = -20012

def IOTC_Get_Version():
    try:
        fn = _lib.IOTC_Get_Version
        fn.argtypes = [ctypes.POINTER(ctypes.c_uint)]
        fn.restype = None
        
        ver = ctypes.c_uint(0)
        fn(ctypes.byref(ver))
        
        # Version is usually packed: Major.Minor.Build.Revision
        # (ver >> 24) & 0xFF, (ver >> 16) & 0xFF, (ver >> 8) & 0xFF, ver & 0xFF
        v = ver.value
        return f"{(v >> 24) & 0xff}.{(v >> 16) & 0xff}.{(v >> 8) & 0xff}.{v & 0xff}"
    except Exception as e:
        print(f"IOTC_Get_Version error: {e}", file=sys.stderr)
        return "Unknown"

def IOTC_Initialize2(udp_port):
    try:
        fn = _lib.IOTC_Initialize2
        fn.argtypes = [ctypes.c_ushort]
        fn.restype = ctypes.c_int
        return fn(udp_port)
    except Exception as e:
        print(f"IOTC_Initialize2 error: {e}", file=sys.stderr)
        return -1

def IOTC_DeInitialize():
    try:
        fn = _lib.IOTC_DeInitialize
        fn.argtypes = []
        fn.restype = ctypes.c_int
        return fn()
    except Exception as e:
        print(f"IOTC_DeInitialize error: {e}", file=sys.stderr)
        return -1

def IOTC_Connect_ByUID_Parallel(uid, sid):
    try:
        fn = _lib.IOTC_Connect_ByUID_Parallel
        fn.argtypes = [ctypes.c_char_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        return fn(uid.encode('utf-8'), sid)
    except Exception as e:
        print(f"IOTC_Connect_ByUID_Parallel error: {e}", file=sys.stderr)
        return -1

def IOTC_Connect_ByUID(uid):
    try:
        fn = _lib.IOTC_Connect_ByUID
        fn.argtypes = [ctypes.c_char_p]
        fn.restype = ctypes.c_int
        return fn(uid.encode('utf-8'))
    except Exception as e:
        print(f"IOTC_Connect_ByUID error: {e}", file=sys.stderr)
        return -1

def IOTC_Session_Close(sid):
    try:
        fn = _lib.IOTC_Session_Close
        fn.argtypes = [ctypes.c_int]
        fn(sid)
    except:
        pass

def avInitialize(max_channel_num):
    try:
        fn = _av_lib.avInitialize
        fn.argtypes = [ctypes.c_int]
        fn.restype = ctypes.c_int
        return fn(max_channel_num)
    except AttributeError:
        # Function might not exist in some versions or variants
        return 0
    except Exception as e:
        print(f"avInitialize error: {e}", file=sys.stderr)
        return -1

def avDeInitialize():
    try:
        fn = _av_lib.avDeInitialize
        fn.argtypes = []
        fn.restype = ctypes.c_int
        return fn()
    except AttributeError:
        return 0
    except Exception as e:
        print(f"avDeInitialize error: {e}", file=sys.stderr)
        return -1

def avClientStart(sid, user, pwd, timeout, serv_type, channel):
    try:
        fn = _av_lib.avClientStart
        # int avClientStart(int SID, const char *account, const char *password, unsigned int timeout, unsigned int *servType, unsigned int channel)
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint]
        fn.restype = ctypes.c_int
        
        serv_type_ref = ctypes.c_uint(serv_type)
        return fn(sid, user.encode('utf-8'), pwd.encode('utf-8'), timeout, ctypes.byref(serv_type_ref), channel)
    except Exception as e:
        print(f"avClientStart error: {e}", file=sys.stderr)
        return -1

def avClientStop(av_index):
    try:
        fn = _av_lib.avClientStop
        fn.argtypes = [ctypes.c_int]
        fn(av_index)
    except:
        pass

def avSendIOCtrl(av_index, type, payload):
    try:
        fn = _av_lib.avSendIOCtrl
        # int avSendIOCtrl(int avIndex, unsigned int ioCtrlType, const char *data, int dataSize);
        fn.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        
        # payload is bytes
        return fn(av_index, type, payload, len(payload))
    except Exception as e:
        print(f"avSendIOCtrl error: {e}", file=sys.stderr)
        return -1

def avRecvFrameData2(av_index, buf, size, out_buf_size, out_frame_size, out_frame_info, frame_idx, key_frame):
    try:
        fn = _av_lib.avRecvFrameData2
        # int avRecvFrameData2(int avIndex, char *buf, int bufSize, int *outBufSize, int *outFrameSize, char *pFrameInfo, int frameInfoSize, int *outFrameIndex);
        
        # We need to handle 'buf' (bytearray) as mutable buffer.
        c_buf = (ctypes.c_char * len(buf)).from_buffer(buf)
        
        c_out_buf_size = ctypes.c_int(0)
        c_out_frame_size = ctypes.c_int(0)
        c_frame_idx = ctypes.c_int(0)
        
        # Frame Info is a struct of size 24 usually. We pass a buffer.
        # SAFEGUARD: Allocate 128 bytes to prevent overflow if struct is larger
        c_frame_info = (ctypes.c_byte * 128)() 
        
        # Args - Try 9 args (including keyFrame pointer)
        fn.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char), ctypes.c_int, 
                       ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                       ctypes.POINTER(ctypes.c_byte), ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                       ctypes.POINTER(ctypes.c_int)]
        fn.restype = ctypes.c_int
        
        c_key_frame = ctypes.c_int(0)

        print(f"DEBUG: Calling avRecvFrameData2(idx={av_index}, buf_len={size}) with 9 args...", file=sys.stderr)
        sys.stderr.flush()

        ret = fn(av_index, c_buf, size, ctypes.byref(c_out_buf_size), ctypes.byref(c_out_frame_size),
                 c_frame_info, 128, ctypes.byref(c_frame_idx), ctypes.byref(c_key_frame))
        
        print(f"DEBUG: avRecvFrameData2 returned {ret}", file=sys.stderr)
        
        if key_frame: key_frame[0] = c_key_frame.value
        sys.stderr.flush()

        # Update python mutable args (lists)
        if out_buf_size: out_buf_size[0] = c_out_buf_size.value
        if out_frame_size: out_frame_size[0] = c_out_frame_size.value
        if frame_idx: frame_idx[0] = c_frame_idx.value
        
        return ret
    except Exception as e:
        print(f"avRecvFrameData2 error: {e}", file=sys.stderr)
        return -1

if __name__ == "__main__":
    print("Loading IOTC library...")
    ver = IOTC_Get_Version()
    print(f"IOTC Version: {ver}")
