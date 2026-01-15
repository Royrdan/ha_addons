import struct
import time
import sys

# Constants found in AVIOCTRLDEFs.java
IOTYPE_USER_IPCAM_START = 0x1FF  # 511
IOTYPE_USER_IPCAM_STOP = 0x2FF   # 767
IOTYPE_USER_IPCAM_AUDIOSTART = 0x300 # 768
IOTYPE_USER_IPCAM_AUDIOSTOP = 0x301  # 769
IOTYPE_USER_IPCAM_SPEAKERSTART = 0x350 # 848
IOTYPE_USER_IPCAM_SPEAKERSTOP = 0x351  # 849

# Payload structure for SMsgAVIoctrlAVStream
# int channel;
# byte[] reserved = new byte[4];
# Total size: 8 bytes

def create_start_stream_payload(channel=0):
    """
    Creates the payload for IOTYPE_USER_IPCAM_START.
    Structure: Channel ID (4 bytes, Little Endian) + 4 bytes padding.
    """
    # struct.pack('<I', channel) packs the channel as a 4-byte little-endian unsigned int
    # + b'\x00' * 4 adds the 4 bytes of reserved padding
    payload = struct.pack('<I', channel) + b'\x00' * 4
    return payload

def start_stream(iotc_session_id, av_channel_id, channel=0):
    """
    Sends the start stream command to the camera.
    """
    try:
        import iotc
        payload = create_start_stream_payload(channel)
        print(f"Sending IOTYPE_USER_IPCAM_START (0x{IOTYPE_USER_IPCAM_START:X})", file=sys.stderr)
        iotc.avSendIOCtrl(av_channel_id, IOTYPE_USER_IPCAM_START, payload)
    except ImportError:
        pass
    except Exception as e:
        print(f"Error sending start command: {e}", file=sys.stderr)

def stop_stream(iotc_session_id, av_channel_id, channel=0):
    """
    Sends the stop stream command.
    """
    try:
        import iotc
        payload = create_start_stream_payload(channel)
        print(f"Sending IOTYPE_USER_IPCAM_STOP (0x{IOTYPE_USER_IPCAM_STOP:X})", file=sys.stderr)
        iotc.avSendIOCtrl(av_channel_id, IOTYPE_USER_IPCAM_STOP, payload)
    except ImportError:
        pass
    except Exception as e:
        print(f"Error sending stop command: {e}", file=sys.stderr)
