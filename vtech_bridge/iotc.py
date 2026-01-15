import ctypes
import os
import sys

# Load Library
# Try /usr/lib first (where Dockerfile will put it)
lib_path = "/usr/lib/libIOTCAPIs.so"
if not os.path.exists(lib_path):
    # Try local
    lib_path = os.path.join(os.path.dirname(__file__), "libIOTCAPIs.so")

try:
    _lib = ctypes.CDLL(lib_path)
except OSError as e:
    print(f"Failed to load library {lib_path}: {e}", file=sys.stderr)
    raise

# Define constants
IOTC_ER_TIMEOUT = -20012

def IOTC_Connect_ByUID_Parallel(uid, sid):
    try:
        fn = _lib.IOTC_Connect_ByUID_Parallel
        fn.argtypes = [ctypes.c_char_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        return fn(uid.encode('utf-8'), sid)
    except Exception as e:
        print(f"IOTC_Connect error: {e}", file=sys.stderr)
        return -1

def avClientStart(sid, user, pwd, timeout, serv_type, channel):
    try:
        fn = _lib.avClientStart
        # int avClientStart(int SID, const char *account, const char *password, unsigned int timeout, unsigned int *servType, unsigned int channel)
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint]
        fn.restype = ctypes.c_int
        
        serv_type_ref = ctypes.c_uint(serv_type)
        return fn(sid, user.encode('utf-8'), pwd.encode('utf-8'), timeout, ctypes.byref(serv_type_ref), channel)
    except Exception as e:
        print(f"avClientStart error: {e}", file=sys.stderr)
        return -1

def avSendIOCtrl(av_index, type, payload):
    try:
        fn = _lib.avSendIOCtrl
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
        fn = _lib.avRecvFrameData2
        # int avRecvFrameData2(int avIndex, char *buf, int bufSize, int *outBufSize, int *outFrameSize, char *pFrameInfo, int frameInfoSize, int *outFrameIndex);
        # Note: frameInfoSize is passed by value, not pointer, in some versions? Or pointer? 
        # Usually: (int avIndex, char *buf, int bufSize, int *outBufSize, int *outFrameSize, FRAMEINFO_t *pFrameInfo, int frameInfoSize, int *outFrameIndex)
        
        # We need to handle 'buf' (bytearray) as mutable buffer.
        c_buf = (ctypes.c_char * len(buf)).from_buffer(buf)
        
        c_out_buf_size = ctypes.c_int(0)
        c_out_frame_size = ctypes.c_int(0)
        c_frame_idx = ctypes.c_int(0)
        
        # Frame Info is a struct of size 24 usually. We pass a buffer.
        # out_frame_info passed from python is [0]*10 (list of ints). We need to fill it? 
        # bridge.py expects C-style pointer returns filling the lists.
        
        # Create a buffer for frame info
        c_frame_info = (ctypes.c_byte * 24)() 
        
        # Args
        fn.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char), ctypes.c_int, 
                       ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                       ctypes.POINTER(ctypes.c_byte), ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        fn.restype = ctypes.c_int
        
        ret = fn(av_index, c_buf, size, ctypes.byref(c_out_buf_size), ctypes.byref(c_out_frame_size),
                 c_frame_info, 24, ctypes.byref(c_frame_idx))
        
        # Update python mutable args
        out_buf_size[0] = c_out_buf_size.value
        out_frame_size[0] = c_out_frame_size.value
        frame_idx[0] = c_frame_idx.value
        # Key frame detection? 
        # Usually byte 17 is keyframe flag? 
        # For now ignore key_frame output update or guess.
        
        return ret
    except Exception as e:
        print(f"avRecvFrameData2 error: {e}", file=sys.stderr)
        return -1

def IOTC_Session_Close(sid):
    try:
        fn = _lib.IOTC_Session_Close
        fn.argtypes = [ctypes.c_int]
        fn(sid)
    except:
        pass

def avClientStop(av_index):
    try:
        fn = _lib.avClientStop
        fn.argtypes = [ctypes.c_int]
        fn(av_index)
    except:
        pass
