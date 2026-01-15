import ctypes
import os
import sys
import time

LIB_DIRS = ["libs/x86", "libs/x86_TS269HX", "libs/x86_X1000"]
UID = ""

def test_lib(path, name):
    print(f"--- Testing {name} ---")
    lib_file = os.path.join(path, "libIOTCAPIs.so")
    if not os.path.exists(lib_file):
        print(f"File not found: {lib_file}")
        return

    try:
        lib = ctypes.CDLL(lib_file)
        print("Loaded library successfully.")
    except OSError as e:
        print(f"Failed to load: {e}")
        return

    try:
        # Check version
        try:
            ver_fn = lib.IOTC_Get_Version
            ver_fn.argtypes = [ctypes.POINTER(ctypes.c_uint)]
            ver = ctypes.c_uint(0)
            ver_fn(ctypes.byref(ver))
            v = ver.value
            version_str = f"{(v >> 24) & 0xff}.{(v >> 16) & 0xff}.{(v >> 8) & 0xff}.{v & 0xff}"
            print(f"Version: {version_str}")
        except:
            print("Could not get version.")
        
        # Initialize
        try:
            init_fn = lib.IOTC_Initialize2
            init_fn.argtypes = [ctypes.c_ushort]
            init_fn.restype = ctypes.c_int
            ret = init_fn(0)
            print(f"Initialize2(0) ret: {ret}")
        except AttributeError:
             # Try IOTC_Initialize
            print("IOTC_Initialize2 not found, trying IOTC_Initialize")
            init_fn = lib.IOTC_Initialize
            init_fn.argtypes = []
            init_fn.restype = ctypes.c_int
            ret = init_fn()
            print(f"IOTC_Initialize ret: {ret}")

        if ret < 0:
            return

        # Connect
        if UID:
            print(f"Attempting Connect to {UID}...")
            # Try Parallel
            try:
                conn_fn = lib.IOTC_Connect_ByUID_Parallel
                conn_fn.argtypes = [ctypes.c_char_p, ctypes.c_int]
                conn_fn.restype = ctypes.c_int
                sid = conn_fn(UID.encode('utf-8'), 0)
                print(f"Connect_Parallel ret: {sid}")
            except AttributeError:
                print("Parallel connect not found.")
                sid = -1
            
            if sid < 0:
                # Try Normal
                try:
                    print("Trying IOTC_Connect_ByUID...")
                    conn_fn2 = lib.IOTC_Connect_ByUID
                    conn_fn2.argtypes = [ctypes.c_char_p]
                    conn_fn2.restype = ctypes.c_int
                    sid = conn_fn2(UID.encode('utf-8'))
                    print(f"Connect_ByUID ret: {sid}")
                except AttributeError:
                    print("Connect_ByUID not found.")

        # Deinit
        try:
            deinit_fn = lib.IOTC_DeInitialize
            deinit_fn()
        except:
            pass
        
    except Exception as e:
        print(f"Error during test: {e}")
    print("--------------------")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        UID = sys.argv[1]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Also test the default one in root/usr/lib
    test_lib("/usr/lib", "INSTALLED_LIB")
    
    for d in LIB_DIRS:
        test_lib(os.path.join(base_dir, d), d)
