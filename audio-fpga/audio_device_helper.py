"""
audio_device_helper.py - Device Auto-Detection for Cancellation Experiments
"""

import sounddevice as sd

def resolve_audio_device(spec, default_type="speaker"):
    """
    Resolves a device specification (index integer, 'speaker', 'headphone', or None)
    to a valid sounddevice device index.
    """
    if spec is None:
        spec = default_type
        
    try:
        # If integer index provided
        dev_idx = int(spec)
        return dev_idx
    except ValueError:
        pass
        
    spec_lower = str(spec).strip().lower()
    devices = sd.query_devices()
    
    if spec_lower == "speaker":
        # Search for monitor / external speaker
        for idx, d in enumerate(devices):
            if d['max_output_channels'] > 0:
                name_l = d['name'].lower()
                if any(k in name_l for k in ['u32r', 'speaker', 'display', 'realtek', 'hd audio']) and not any(k in name_l for k in ['headphone', 'headset', 'buds']):
                    return idx
        # Fallback to non-headphone output
        for idx, d in enumerate(devices):
            if d['max_output_channels'] > 0 and 'head' not in d['name'].lower():
                return idx
                
    elif spec_lower in ["headphone", "headset", "headphones"]:
        # Search for headphones / headsets
        for idx, d in enumerate(devices):
            if d['max_output_channels'] > 0:
                name_l = d['name'].lower()
                if any(k in name_l for k in ['wh-ch', 'buds', 'headphone', 'headset']):
                    return idx
                    
    # Ultimate fallback to system default output
    return sd.default.device[1]

def get_device_name(dev_idx):
    try:
        return sd.query_devices(dev_idx)['name']
    except Exception:
        return f"Device {dev_idx}"
