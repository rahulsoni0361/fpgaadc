#!/usr/bin/env python3
"""
list_audio_devices.py - Audio Output Device Enumerator
Categorizes available output endpoints into Headphones vs Speakers.
"""

import sounddevice as sd

def list_devices():
    devices = sd.query_devices()
    default_out = sd.default.device[1]
    
    print("=" * 75)
    print(" DETECTED AUDIO OUTPUT DEVICES ON YOUR SYSTEM")
    print("=" * 75)
    
    headphones = []
    speakers = []
    others = []
    
    for idx, d in enumerate(devices):
        if d['max_output_channels'] > 0:
            name = d['name']
            api_name = sd.query_hostapis(d['hostapi'])['name']
            is_default = (idx == default_out)
            def_mark = " [SYSTEM DEFAULT]" if is_default else ""
            
            entry = (idx, name, api_name, def_mark)
            name_lower = name.lower()
            if any(k in name_lower for k in ['headphone', 'headset', 'buds', 'ear']):
                headphones.append(entry)
            elif any(k in name_lower for k in ['speaker', 'display', 'u32r', 'realtek', 'hd audio']):
                speakers.append(entry)
            else:
                others.append(entry)
                
    print("\n[HEADPHONES / HEADSETS] (For Anti-Phase Cancellation Tone):")
    for idx, name, api, def_mark in headphones:
        print(f"  Device [{idx:02d}]: {name:<40} ({api}){def_mark}")
        
    print("\n[SPEAKERS / MONITORS] (For Reference Ambient Sound):")
    for idx, name, api, def_mark in speakers:
        print(f"  Device [{idx:02d}]: {name:<40} ({api}){def_mark}")
        
    if others:
        print("\n[OTHER AUDIO OUTPUTS]:")
        for idx, name, api, def_mark in others:
            print(f"  Device [{idx:02d}]: {name:<40} ({api}){def_mark}")
            
    print("\n" + "=" * 75)
    return headphones, speakers

if __name__ == "__main__":
    list_devices()
