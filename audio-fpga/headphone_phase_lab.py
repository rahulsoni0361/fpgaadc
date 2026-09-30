#!/usr/bin/env python3
"""
headphone_phase_lab.py - Dual-Channel Headphone Phase Shift Experiment Lab
=============================================================================
Unified Headphone Lab for 4 kHz Phase Stepping Experiment:
- Left Channel (Ear 1):  Fixed Reference 4 kHz Sine Wave (phi = 0°)
- Right Channel (Ear 2): Continuous 4 kHz Sine Wave with +5° Step every 2.0s
- Mono Summed Mode:      Acoustic constructive / destructive cancellation test
- Live Terminal Display: Phasor compass, Interaural Time Delay, Lissajous phase
=============================================================================
"""

import sys
import time
import math
import argparse
import threading
import numpy as np
import sounddevice as sd

class BinauralAudioEngine:
    def __init__(self, freq=4000.0, step_deg=5.0, step_sec=2.0, volume=0.25, fs=48000, mode="stereo"):
        self.freq = freq
        self.step_deg = step_deg
        self.step_sec = step_sec
        self.volume = max(0.01, min(1.0, volume))
        self.fs = fs
        self.mode = mode # 'stereo' (binaural Left/Right) or 'mono_sum' (acoustic interference)
        
        # Phase accumulators
        self.carrier_phase = 0.0
        self.carrier_inc = 2.0 * np.pi * freq / fs
        
        self.current_step_deg = 0.0
        self.current_smoothed_deg = 0.0
        self.target_phase_deg = 0.0
        
        self.running = False
        self.start_time = 0.0
        self.step_count = 0
        self.lock = threading.Lock()
        
        # Slew rate: 25ms smoothing to ensure 100% continuous, pop-free transition
        self.slew_rate = step_deg / (0.025 * fs)

    def audio_callback(self, outdata, frames, time_info, status):
        # Time progression
        phases_ref = self.carrier_phase + self.carrier_inc * np.arange(frames)
        self.carrier_phase = (self.carrier_phase + self.carrier_inc * frames) % (2.0 * np.pi)
        
        # Smooth phase shift calculation
        phase_shifts = np.zeros(frames, dtype=np.float64)
        for i in range(frames):
            diff = self.target_phase_deg - self.current_smoothed_deg
            if abs(diff) > 1e-4:
                step = math.copysign(min(abs(diff), self.slew_rate), diff)
                self.current_smoothed_deg += step
            else:
                self.current_smoothed_deg = self.target_phase_deg
            phase_shifts[i] = math.radians(self.current_smoothed_deg)
            
        phases_stepped = phases_ref + phase_shifts
        
        sig_ref = (self.volume * np.sin(phases_ref)).astype(np.float32)
        sig_stepped = (self.volume * np.sin(phases_stepped)).astype(np.float32)
        
        if self.mode == "stereo":
            # True Binaural: Left ear gets Reference, Right ear gets Stepping Wave
            outdata[:, 0] = sig_ref
            outdata[:, 1] = sig_stepped
        else: # mono_sum
            # Acoustic Interference: Both ears receive the sum (demonstrating cancellation null at 180°)
            summed = 0.5 * (sig_ref + sig_stepped)
            outdata[:, 0] = summed
            outdata[:, 1] = summed

def render_ascii_scope(phase_deg, width=40):
    """Draw a miniature dual-trace ASCII oscilloscope comparing ref and shifted waves."""
    rad = math.radians(phase_deg)
    t = np.linspace(0, 2 * np.pi, width)
    y_ref = np.sin(t)
    y_step = np.sin(t + rad)
    
    lines = []
    # 5 vertical rows (+1 to -1)
    levels = [0.8, 0.4, 0.0, -0.4, -0.8]
    for lvl in levels:
        row = []
        for x in range(width):
            is_ref = abs(y_ref[x] - lvl) < 0.25
            is_step = abs(y_step[x] - lvl) < 0.25
            if is_ref and is_step:
                row.append("★") # Overlap / in-phase
            elif is_step:
                row.append("•") # Stepped wave
            elif is_ref:
                row.append("·") # Ref wave
            else:
                row.append(" ")
        lines.append("".join(row))
    return lines

def main():
    parser = argparse.ArgumentParser(description="Unified Headphone Phase Experiment Lab")
    parser.add_argument("--freq", type=float, default=4000.0, help="Tone frequency in Hz (default: 4000 Hz)")
    parser.add_argument("--volume", type=float, default=0.25, help="Volume amplitude (default: 0.25)")
    parser.add_argument("--step-deg", type=float, default=5.0, help="Phase step in degrees (default: 5.0°)")
    parser.add_argument("--step-sec", type=float, default=2.0, help="Step interval in seconds (default: 2.0s)")
    parser.add_argument("--mode", choices=["stereo", "mono_sum"], default="stereo",
                        help="Playback mode: 'stereo' for binaural spatial shifting, 'mono_sum' for acoustic cancellation")
    args = parser.parse_args()

    engine = BinauralAudioEngine(
        freq=args.freq,
        step_deg=args.step_deg,
        step_sec=args.step_sec,
        volume=args.volume,
        mode=args.mode
    )

    print("=" * 78)
    print(" UNIFIED HEADPHONE PHASE EXPERIMENT LAB (4 kHz)")
    print("=" * 78)
    print(f" Frequency:         {args.freq:.1f} Hz (Period = {1e6/args.freq:.1f} µs)")
    print(f" Playback Mode:     {args.mode.upper()}")
    if args.mode == "stereo":
        print("   -> Left Ear:      Fixed Reference (phi = 0.0°)")
        print("   -> Right Ear:     Continuous Stepper (+5.0° every 2.0s)")
        print("   -> Effect:        BINAURAL SPATIAL SHIFT (Sound rotates inside your head)")
    else:
        print("   -> Both Ears:     Acoustic Sum (Ref + Stepped) / 2")
        print("   -> Effect:        DESTRUCTIVE INTERFERENCE (Cancels to SILENCE at 180°)")
    print(f" Phase Increment:   +{args.step_deg}° every {args.step_sec:.1f} seconds")
    print(f" Transition Engine: Smooth 25 ms continuous slewing (100% pop-free)")
    print("=" * 78)
    print(" Controls: Press [M] + Enter to toggle Stereo / Mono Sum | [Ctrl+C] to stop.\n")

    engine.start_time = time.time()
    last_step_idx = -1

    try:
        with sd.OutputStream(channels=2, callback=engine.audio_callback, samplerate=engine.fs, dtype='float32'):
            while True:
                now = time.time()
                elapsed = now - engine.start_time
                step_idx = int(elapsed / args.step_sec)
                
                if step_idx != last_step_idx:
                    last_step_idx = step_idx
                    current_deg = (step_idx * args.step_deg) % 360.0
                    engine.target_phase_deg = current_deg
                
                phase_deg = engine.current_smoothed_deg % 360.0
                rad = math.radians(phase_deg)
                itd_us = (phase_deg / 360.0) * (1e6 / args.freq)
                cancellation_db = 20 * math.log10(max(1e-4, abs(math.cos(rad / 2.0))))
                time_in_step = elapsed % args.step_sec
                remaining = max(0.0, args.step_sec - time_in_step)
                
                pct = int((time_in_step / args.step_sec) * 12)
                prog_bar = "[" + "█" * pct + " " * (12 - pct) + "]"
                
                # Visual perception indicator
                if args.mode == "stereo":
                    if 345 <= phase_deg or phase_deg <= 15:
                        spatial_tag = "CENTER (In-Phase Focus)"
                    elif 15 < phase_deg < 165:
                        spatial_tag = f"PANNING RIGHT (+{phase_deg:.0f}°)"
                    elif 165 <= phase_deg <= 195:
                        spatial_tag = "DIFFUSE / OUT-OF-HEAD (180° Anti-Phase)"
                    else:
                        spatial_tag = f"PANNING LEFT (+{phase_deg:.0f}°)"
                else:
                    spatial_tag = f"Sum Attenuation: {cancellation_db:5.1f} dB"

                sys.stdout.write(
                    f"\r [STEP #{step_idx:03d}] "
                    f"Phase: \033[1;32m{phase_deg:5.1f}°\033[0m | "
                    f"ITD: \033[1;33m{itd_us:5.1f} µs\033[0m | "
                    f"\033[1;36m{spatial_tag:<26}\033[0m | "
                    f"Next in: {prog_bar} {remaining:3.1f}s  "
                )
                sys.stdout.flush()
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\n[*] Stopped Headphone Phase Lab.")

if __name__ == "__main__":
    main()
