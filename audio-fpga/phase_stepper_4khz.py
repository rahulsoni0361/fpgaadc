#!/usr/bin/env python3
"""
phase_stepper_4khz.py - 4 kHz Phase Stepper (Headphone Output)
=============================================================================
Program 2 of 2: Plays a continuous 4 kHz sine wave whose phase steps by +5°
every 2.0 seconds through your HEADPHONES to test acoustic cancellation against
an external speaker playing the reference tone.
=============================================================================
"""

import sys
import time
import math
import argparse
import numpy as np
import sounddevice as sd
from audio_device_helper import resolve_audio_device, get_device_name

def draw_phasor_compass(phase_deg):
    """Render a compact 2D ASCII vector compass showing the current phase angle."""
    rad = math.radians(phase_deg)
    arrows = ["→ (0°)", "↗ (45°)", "↑ (90°)", "↖ (135°)", "← (180° NULL)", "↙ (225°)", "↓ (270°)", "↘ (315°)"]
    idx = int(round((phase_deg % 360) / 45)) % 8
    arrow_str = arrows[idx]
    
    # Interference amplitude: 2*cos(phi/2)
    interf_factor = abs(math.cos(rad / 2.0)) # 0.0 (null cancellation) to 1.0 (reinforcement)
    interf_bars = "█" * int(interf_factor * 10) + "░" * (10 - int(interf_factor * 10))
    
    return arrow_str, interf_factor, interf_bars

def main():
    parser = argparse.ArgumentParser(description="4 kHz Continuous Phase Stepper for Headphone Acoustic Cancellation")
    parser.add_argument("--freq", type=float, default=4000.0, help="Tone frequency in Hz (default: 4000 Hz)")
    parser.add_argument("--volume", type=float, default=0.25, help="Audio amplitude (0.01 to 1.0, default: 0.25)")
    parser.add_argument("--device", default="headphone", help="Audio output device index, 'headphone', or 'speaker' (default: headphone)")
    parser.add_argument("--step-deg", type=float, default=5.0, help="Phase step in degrees (default: 5.0°)")
    parser.add_argument("--step-sec", type=float, default=2.0, help="Interval between steps in seconds (default: 2.0s)")
    parser.add_argument("--channel", choices=["both", "left", "right"], default="both",
                        help="Headphone output channels (default: both ears for full ambient cancellation)")
    parser.add_argument("--samplerate", type=int, default=48000, help="Audio sample rate (default: 48000)")
    args = parser.parse_args()

    dev_idx = resolve_audio_device(args.device, default_type="headphone")
    dev_name = get_device_name(dev_idx)

    fs = args.samplerate
    freq = args.freq
    vol = max(0.01, min(1.0, args.volume))
    step_deg = args.step_deg
    step_sec = args.step_sec

    # Wavelength at 4 kHz (speed of sound c = 343 m/s)
    speed_of_sound = 343.0 # m/s
    wavelength_cm = (speed_of_sound / freq) * 100.0 # 8.575 cm

    # State variables
    carrier_phase = 0.0
    carrier_inc = 2.0 * np.pi * freq / fs
    
    current_phase_offset = 0.0 # Current smoothed phase offset in radians
    target_phase_offset = 0.0  # Target phase offset in radians
    
    start_time = time.time()
    last_step_idx = -1

    # Slew rate: smoothly interpolate phase over 25 ms (1200 samples) to prevent pops/clicks
    slew_samples = int(0.025 * fs)
    slew_step = (math.radians(step_deg) / slew_samples) if slew_samples > 0 else 0.01

    def audio_callback(outdata, frames, time_info, status):
        nonlocal carrier_phase, current_phase_offset, target_phase_offset
        if status:
            pass

        # Generate sample-by-sample phase offset array with smooth slew
        phase_offsets = np.zeros(frames, dtype=np.float64)
        for i in range(frames):
            if abs(current_phase_offset - target_phase_offset) > 1e-5:
                diff = target_phase_offset - current_phase_offset
                if abs(diff) <= slew_step:
                    current_phase_offset = target_phase_offset
                else:
                    current_phase_offset += math.copysign(slew_step, diff)
            phase_offsets[i] = current_phase_offset

        # Carrier phase progression
        carrier_phases = carrier_phase + carrier_inc * np.arange(frames)
        carrier_phase = (carrier_phase + carrier_inc * frames) % (2.0 * np.pi)

        # Output signal with continuous phase modulation
        total_phases = carrier_phases + phase_offsets
        samples = (vol * np.sin(total_phases)).astype(np.float32)

        # Route channels
        if args.channel == "both":
            outdata[:, 0] = samples
            outdata[:, 1] = samples
        elif args.channel == "left":
            outdata[:, 0] = samples
            outdata[:, 1] = 0.0
        else: # right
            outdata[:, 0] = 0.0
            outdata[:, 1] = samples

    print("=" * 76)
    print(" PROGRAM 2: CONTINUOUS 4 kHz PHASE STEPPER (HEADPHONE OUTPUT)")
    print("=" * 76)
    print(f" Frequency:         {freq:.1f} Hz (Wavelength lambda = {wavelength_cm:.2f} cm)")
    print(f" Audio Device:      [{dev_idx:02d}] {dev_name}")
    print(f" Headphone Routing: {args.channel.upper()} earcups")
    print(f" Phase Increment:   +{step_deg}° every {step_sec:.1f} seconds")
    print(f" Distance Equiv:    {wavelength_cm * (step_deg / 360.0) * 10:.2f} mm acoustic shift per step")
    print(f" Transition Engine: Smooth continuous slewing (100% pop/click-free)")
    print("-" * 76)
    print(" ACOUSTIC CANCELLATION PRINCIPLE:")
    print(" • The speaker plays 4 kHz into the room air.")
    print(" • This headphone plays 4 kHz directly at your eardrum.")
    print(" • Every 2 seconds, the phase steps by 5° (shifting acoustic timing).")
    print(" • When the phase matches 180° anti-phase relative to the speaker sound,")
    print("   the physical air pressure waves destructively interfere at your eardrum,")
    print("   creating a noticeable ACOUSTIC CANCELLATION NULL (SILENCE)!")
    print("=" * 76)
    print(" Starting continuous headphone playback... Press Ctrl+C to stop.\n")

    try:
        with sd.OutputStream(device=dev_idx, channels=2, callback=audio_callback, samplerate=fs, dtype='float32'):
            while True:
                now = time.time()
                elapsed = now - start_time
                current_step_idx = int(elapsed / step_sec)
                
                # Check for step transition
                if current_step_idx != last_step_idx:
                    last_step_idx = current_step_idx
                    current_deg = (current_step_idx * step_deg) % 360.0
                    target_phase_offset = math.radians(current_deg)
                
                # Metrics calculation
                phase_deg = math.degrees(current_phase_offset) % 360.0
                itd_us = (phase_deg / 360.0) * (1e6 / freq) # Time shift in microseconds
                dist_shift_mm = (phase_deg / 360.0) * wavelength_cm * 10.0 # mm
                time_in_step = elapsed % step_sec
                remaining = max(0.0, step_sec - time_in_step)
                
                arrow_str, interf_factor, interf_bars = draw_phasor_compass(phase_deg)
                
                # Countdown bar
                pct = int((time_in_step / step_sec) * 10)
                prog_bar = "[" + "█" * pct + " " * (10 - pct) + "]"
                
                # Cancellation status tag
                if 170.0 <= phase_deg <= 190.0:
                    status_tag = "\033[1;31m[** CANCELLATION NULL **]\033[0m"
                elif 350.0 <= phase_deg or phase_deg <= 10.0:
                    status_tag = "\033[1;32m[ REINFORCEMENT PEAK ]\033[0m"
                else:
                    status_tag = f"Air Path: +{dist_shift_mm:4.1f}mm"

                # Status print
                sys.stdout.write(
                    f"\r [STEP #{current_step_idx:03d}] "
                    f"Phase: \033[1;36m{phase_deg:5.1f}°\033[0m {arrow_str:<12} | "
                    f"dT: {itd_us:5.1f}µs | "
                    f"{status_tag:<26} | "
                    f"Next in: {prog_bar} {remaining:3.1f}s   "
                )
                sys.stdout.flush()
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\n[*] Stopped phase stepper.")

if __name__ == "__main__":
    main()
