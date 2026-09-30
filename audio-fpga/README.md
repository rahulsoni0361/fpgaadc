# 4 kHz Continuous Acoustic Cancellation & Binaural Phase Experiment

This lab implements the **Active Acoustic Cancellation (ANC)** and phase-stepping experiment specified in [`specs.md`](specs.md).

---

## The Concept of Acoustic Cancellation

A 4 kHz sound wave emitted by your external room speaker travels through the air to your ears:
$$P_{\text{speaker}}(t) = A_1 \sin(2\pi f t + \phi_{\text{distance}})$$

Simultaneously, your headphones emit a tone directly at your eardrum:
$$P_{\text{headphone}}(t) = A_2 \sin(2\pi f t + \phi_{\text{stepper}})$$

At the eardrum, the two acoustic pressure waves superimpose:
$$P_{\text{total}}(t) = P_{\text{speaker}}(t) + P_{\text{headphone}}(t)$$

When the headphone phase matches **$180^\circ$ anti-phase** relative to the arriving speaker wave ($\phi_{\text{stepper}} = \phi_{\text{distance}} + 180^\circ$) and amplitudes match ($A_1 \approx A_2$), the physical sound waves **destructively cancel out into an acoustic silence null at your eardrums!**

---

## Method A: The Two Separate Python Programs

You can run both programs concurrently in separate terminal windows. Both audio streams are **100% continuous** with zero pops or buffer clicks:

### Terminal 1: [ref_4khz.py](ref_4khz.py) (Room Speaker)
Plays the continuous reference 4 kHz tone through your **ROOM SPEAKER**:
```bash
uv run --with sounddevice,numpy python ref_4khz.py --device speaker --volume 0.20
```

### Terminal 2: [phase_stepper_4khz.py](phase_stepper_4khz.py) (Headphones)
Plays the continuous 4 kHz tone with $+5^\circ$ phase stepping every 2.0s through your **HEADPHONES**:
```bash
uv run --with sounddevice,numpy python phase_stepper_4khz.py --device headphone --volume 0.20
```
- Every 2 seconds, the phase steps by $5^\circ$ ($1.19\text{ mm}$ acoustic path shift).
- Watch the live terminal phasor vector rotate toward $180^\circ$ and listen for the speaker tone disappearing at your ears!

---

## Method B: Unified Interactive Cancellation Rig: [acoustic_cancellation_lab.py](acoustic_cancellation_lab.py)

If you want to control both the room speaker and the headphones from a single terminal with interactive real-time tuning:

```bash
uv run --with sounddevice,numpy python acoustic_cancellation_lab.py
```

### Interactive Real-Time Key Controls:
- **`[SPACE]`**: **FREEZE / LOCK** the auto-stepping when you hear the cancellation null!
- **`[+]` / `[-]`** (or Left/Right arrows): **Nudge phase by $\pm 1.0^\circ$** to lock onto the deepest acoustic silence null.
- **`[UP]` / `[DOWN]`** arrows: Adjust headphone volume to match the acoustic sound pressure of the speaker at your ear.
- **`[S]`**: Mute / Unmute the speaker to verify how loud the speaker actually was before cancellation.
- **`[Ctrl+C]`**: Exit cleanly.

---

## Device Enumeration Utility

To inspect the device IDs detected on your system:
```bash
uv run --with sounddevice python list_audio_devices.py
```
