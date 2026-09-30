#!/usr/bin/env python3
"""
acoustic_cancellation_lab.py - Dual-Device Speaker + Headphone Cancellation Rig
=============================================================================
Active Acoustic Cancellation Rig:
- Device 1 (Room Speaker):     Plays continuous 4 kHz reference sine wave
- Device 2 (Worn Headphones):  Plays continuous 4 kHz sine wave with phase stepping

Interactive Real-Time Controls:
- [SPACE] : Freeze / Resume auto-stepping (to lock onto the cancellation null)
- [Left / Right] : Fine-tune phase by +/- 1.0°
- [Up / Down]    : Adjust headphone volume to match speaker sound level
- [S]            : Mute / Unmute Speaker (to A/B test ambient level)
- [Ctrl+C]       : Stop experiment
=============================================================================
"""

import sys
import time
import math
import argparse
import threading
import numpy as np
import sounddevice as sd
from audio_device_helper import resolve_audio_device, get_device_name

class AcousticCancellationEngine:
    def __init__(self, freq=4000.0, step_deg=5.0, step_sec=2.0, spk_vol=0.20, hp_vol=0.20,
                 spk_dev="speaker", hp_dev="headphone", fs=48000):
        self.freq = freq
        self.step_deg = step_deg
        self.step_sec = step_sec
        self.spk_vol = max(0.0, min(1.0, spk_vol))
        self.hp_vol = max(0.0, min(1.0, hp_vol))
        self.fs = fs
        
        self.spk_dev_idx = resolve_audio_device(spk_dev, default_type="speaker")
        self.hp_dev_idx = resolve_audio_device(hp_dev, default_type="headphone")
        
        self.spk_name = get_device_name(self.spk_dev_idx)
        self.hp_name = get_device_name(self.hp_dev_idx)
        
        # Phase accumulators
        self.carrier_phase = 0.0
        self.carrier_inc = 2.0 * np.pi * freq / fs
        
        self.current_smoothed_deg = 0.0
        self.target_phase_deg = 0.0
        self.slew_rate = 5.0 / (0.025 * fs) # 25ms smoothing
        
        self.auto_step = True
        self.spk_muted = False
        self.hp_muted = False
        
        self.start_time = 0.0
        self.lock = threading.Lock()

    def speaker_callback(self, outdata, frames, time_info, status):
        # Speaker emits clean reference (phase = 0.0)
        phases = self.carrier_phase + self.carrier_inc * np.arange(frames)
        # We do not advance carrier_phase here, the headphone callback advances it
        # or we calculate phase from absolute wall-clock time
        vol = 0.0 if self.spk_muted else self.spk_vol
        samples = (vol * np.sin(phases)).astype(np.float32)
        outdata[:, 0] = samples
        outdata[:, 1] = samples

    def headphone_callback(self, outdata, frames, time_info, status):
        # Advance common phase base
        phases_base = self.carrier_phase + self.carrier_inc * np.arange(frames)
        self.carrier_phase = (self.carrier_phase + self.carrier_inc * frames) % (2.0 * np.pi)
        
        # Smooth phase transition
        phase_offsets = np.zeros(frames, dtype=np.float64)
        for i in range(frames):
            diff = self.target_phase_deg - self.current_smoothed_deg
            if abs(diff) > 1e-4:
                step = math.copysign(min(abs(diff), self.slew_rate), diff)
                self.current_smoothed_deg += step
            else:
                self.current_smoothed_deg = self.target_phase_deg
            phase_offsets[i] = math.radians(self.current_smoothed_deg)
            
        vol = 0.0 if self.hp_muted else self.hp_vol
        samples = (vol * np.sin(phases_base + phase_offsets)).astype(np.float32)
        outdata[:, 0] = samples
        outdata[:, 1] = samples

def main():
    parser = argparse.ArgumentParser(description="Active Acoustic Cancellation Rig (Speaker + Headphone)")
    parser.add_argument("--freq", type=float, default=4000.0, help="Tone frequency (default: 4000 Hz)")
    parser.add_argument("--spk-dev", default="speaker", help="Speaker device index or 'speaker'")
    parser.add_argument("--hp-dev", default="headphone", help="Headphone device index or 'headphone'")
    parser.add_argument("--spk-vol", type=float, default=0.20, help="Speaker volume (default: 0.20)")
    parser.add_argument("--hp-vol", type=float, default=0.20, help="Headphone volume (default: 0.20)")
    parser.add_argument("--step-deg", type=float, default=5.0, help="Auto phase step in degrees (default: 5.0°)")
    parser.add_argument("--step-sec", type=float, default=2.0, help="Step interval in seconds (default: 2.0s)")
    args = parser.parse_args()

    engine = AcousticCancellationEngine(
        freq=args.freq,
        step_deg=args.step_deg,
        step_sec=args.step_sec,
        spk_vol=args.spk_vol,
        hp_vol=args.hp_vol,
        spk_dev=args.spk_dev,
        hp_dev=args.hp_dev
    )

    wavelength_cm = (343.0 / args.freq) * 100.0

    print("=" * 78)
    print(" ACTIVE ACOUSTIC CANCELLATION RIG (SPEAKER + HEADPHONE)")
    print("=" * 78)
    print(f" Frequency:         {args.freq:.1f} Hz (Acoustic Wavelength = {wavelength_cm:.2f} cm)")
    print(f" Speaker Device:    [{engine.spk_dev_idx:02d}] {engine.spk_name} (Vol: {engine.spk_vol:.2f})")
    print(f" Headphone Device:  [{engine.hp_dev_idx:02d}] {engine.hp_name} (Vol: {engine.hp_vol:.2f})")
    print(f" Auto Phase Step:   +{args.step_deg}° every {args.step_sec:.1f}s")
    print("-" * 78)
    print(" REAL-TIME INTERACTION KEYS:")
    print("  [SPACE]     : FREEZE / RESUME auto-stepping (lock onto the silence null)")
    print("  [+] / [-]   : Nudge phase by +/- 1.0° (fine-tune the null)")
    print("  [UP] / [DN] : Nudge headphone volume by +/- 0.02 (match acoustic pressure)")
    print("  [S]         : Mute / Unmute Speaker (A/B test cancellation effect)")
    print("  [Ctrl+C]    : Stop experiment")
    print("=" * 78)

    engine.start_time = time.time()
    last_step_idx = -1
    paused = False

    # Windows non-blocking key input handler
    try:
        import msvcrt
        def check_key():
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in [b' ', b'p']:
                    return 'toggle_pause'
                elif ch in [b'+', b'=']:
                    return 'phase_up'
                elif ch in [b'-', b'_']:
                    return 'phase_down'
                elif ch in [b's', b'S']:
                    return 'toggle_spk'
                elif ch == b'\xe0': # Special key (arrows)
                    ext = msvcrt.getch()
                    if ext == b'H': return 'vol_up'   # Up
                    elif ext == b'P': return 'vol_down' # Down
                    elif ext == b'M': return 'phase_up'  # Right
                    elif ext == b'K': return 'phase_down'# Left
            return None
    except ImportError:
        def check_key():
            return None

    try:
        # Start both audio streams concurrently
        with sd.OutputStream(device=engine.spk_dev_idx, channels=2, callback=engine.speaker_callback,
                             samplerate=engine.fs, dtype='float32'), \
             sd.OutputStream(device=engine.hp_dev_idx, channels=2, callback=engine.headphone_callback,
                             samplerate=engine.fs, dtype='float32'):

            step_accum = 0.0
            last_t = time.time()

            while True:
                now = time.time()
                dt = now - last_t
                last_t = now

                # Key controls
                k = check_key()
                if k == 'toggle_pause':
                    paused = not paused
                elif k == 'phase_up':
                    engine.target_phase_deg = (engine.target_phase_deg + 1.0) % 360.0
                elif k == 'phase_down':
                    engine.target_phase_deg = (engine.target_phase_deg - 1.0) % 360.0
                elif k == 'vol_up':
                    engine.hp_vol = min(1.0, engine.hp_vol + 0.02)
                elif k == 'vol_down':
                    engine.hp_vol = max(0.01, engine.hp_vol - 0.02)
                elif k == 'toggle_spk':
                    engine.spk_muted = not engine.spk_muted

                # Auto stepping progression
                if not paused:
                    step_accum += dt
                    if step_accum >= args.step_sec:
                        step_accum -= args.step_sec
                        engine.target_phase_deg = (engine.target_phase_deg + args.step_deg) % 360.0

                phase_deg = engine.current_smoothed_deg % 360.0
                rad = math.radians(phase_deg)
                time_shift_us = (phase_deg / 360.0) * (1e6 / args.freq)
                dist_shift_mm = (phase_deg / 360.0) * wavelength_cm * 10.0

                state_str = "\033[1;33m[FROZEN]\033[0m" if paused else "\033[1;32m[STEPPING]\033[0m"
                spk_str = "[SPK: MUTED]" if engine.spk_muted else f"[SPK: {engine.spk_vol:.2f}]"
                
                # Highlight cancellation proximity
                if 170.0 <= phase_deg <= 190.0:
                    status_banner = "\033[1;31m[** NEAR CANCELLATION NULL **]\033[0m"
                else:
                    status_banner = f"Path Shift: +{dist_shift_mm:4.1f}mm"

                sys.stdout.write(
                    f"\r {state_str} "
                    f"Phase: \033[1;36m{phase_deg:5.1f}°\033[0m | "
                    f"HP Vol: \033[1;32m{engine.hp_vol:.2f}\033[0m | "
                    f"{spk_str} | "
                    f"dt: {time_shift_us:5.1f}µs | "
                    f"{status_banner:<28} "
                )
                sys.stdout.flush()
                time.sleep(0.04)

    except KeyboardInterrupt:
        print("\n\n[*] Stopped Acoustic Cancellation Lab.")

if __name__ == "__main__":
    main()
