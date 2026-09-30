#!/usr/bin/env python3
"""
ref_4khz.py - Reference 4 kHz Sine Tone Generator (Speaker Output)
=============================================================================
Program 1 of 2: Generates a continuous, phase-coherent reference 4 kHz sine wave.
Defaults to playing through the ROOM SPEAKER for acoustic cancellation testing.
=============================================================================
"""

import sys
import time
import argparse
import numpy as np
import sounddevice as sd
from audio_device_helper import resolve_audio_device, get_device_name

def main():
    parser = argparse.ArgumentParser(description="Reference 4 kHz Sine Wave Generator")
    parser.add_argument("--freq", type=float, default=4000.0, help="Tone frequency in Hz (default: 4000 Hz)")
    parser.add_argument("--volume", type=float, default=0.25, help="Audio amplitude (0.01 to 1.0, default: 0.25)")
    parser.add_argument("--device", default="speaker", help="Output device index, 'speaker', or 'headphone' (default: speaker)")
    parser.add_argument("--channel", choices=["left", "right", "both"], default="both",
                        help="Output channel (default: both, for room speakers)")
    parser.add_argument("--samplerate", type=int, default=48000, help="Audio sample rate (default: 48000)")
    args = parser.parse_args()

    dev_idx = resolve_audio_device(args.device, default_type="speaker")
    dev_name = get_device_name(dev_idx)

    fs = args.samplerate
    freq = args.freq
    vol = max(0.01, min(1.0, args.volume))
    
    # State tracking for continuous phase accumulator (prevents pops / discontinuities)
    phase = 0.0
    phase_increment = 2.0 * np.pi * freq / fs

    def audio_callback(outdata, frames, time_info, status):
        nonlocal phase
        if status:
            pass
        
        # Vectorized phase accumulation
        phases = phase + phase_increment * np.arange(frames)
        samples = (vol * np.sin(phases)).astype(np.float32)
        phase = (phase + phase_increment * frames) % (2.0 * np.pi)

        # Route channels
        if args.channel == "left":
            outdata[:, 0] = samples
            outdata[:, 1] = 0.0
        elif args.channel == "right":
            outdata[:, 0] = 0.0
            outdata[:, 1] = samples
        else: # both
            outdata[:, 0] = samples
            outdata[:, 1] = samples

    print("=" * 75)
    print(" PROGRAM 1: REFERENCE 4 kHz TONE (ROOM SPEAKER OUTPUT)")
    print("=" * 75)
    print(f" Frequency:         {freq:.1f} Hz (Period: {1e6/freq:.1f} µs)")
    print(f" Audio Device:      [{dev_idx:02d}] {dev_name}")
    print(f" Output Routing:    {args.channel.upper()} channels")
    print(f" Output Amplitude:  {vol:.2f} (-{20*np.log10(1/vol):.1f} dBFS)")
    print(f" Sample Rate:       {fs} Hz")
    print(f" Phase Baseline:    phi = 0.0° (Fixed Reference)")
    print("-" * 75)
    print(" ACOUSTIC CANCELLATION EXPERIMENT:")
    print(" 1. This program plays the continuous 4 kHz sound through your SPEAKER.")
    print(" 2. Wear your headphones.")
    print(" 3. In another terminal, run Program 2 (plays anti-phase sound in headphones):")
    print("    uv run --with sounddevice,numpy python phase_stepper_4khz.py --device headphone")
    print(" 4. As the headphone phase steps by 5°, you will hear the speaker sound")
    print("    cancel out into an acoustic silence null at your ears!")
    print("=" * 75)
    print(" Playing continuous tone through speaker... Press Ctrl+C to stop.\n")

    try:
        with sd.OutputStream(device=dev_idx, channels=2, callback=audio_callback, samplerate=fs, dtype='float32'):
            start_t = time.time()
            wave_chars = ["_", ".", "-", "`", "'", "`", "-", ".", "_"]
            while True:
                elapsed = time.time() - start_t
                anim_idx = int(elapsed * 8) % len(wave_chars)
                bar = "".join(wave_chars[(anim_idx + i) % len(wave_chars)] for i in range(24))
                sys.stdout.write(f"\r [SPEAKER PLAYING]  t={elapsed:6.1f}s | {bar} | 4000 Hz Ref -> {dev_name[:28]} ")
                sys.stdout.flush()
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n[*] Stopped speaker reference tone.")

if __name__ == "__main__":
    main()
