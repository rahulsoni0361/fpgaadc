[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# Matched Filter Bank

The **Matched Filter Bank** is an array of parallel linear filters designed to maximize the output Signal-to-Noise Ratio (SNR) in the presence of stochastic noise.

## Mathematical Formulation

For an incoming discrete signal window $x[n]$ and a known reference signature template $h[m]$ of length $M$, the cross-correlation output is:

$$C[n] = \sum_{m=0}^{M-1} x[n+m] \cdot h[m]$$

To produce a scale-invariant confidence score between $0.0$ and $1.0$, we compute the **Normalized Cross-Correlation**:

$$\rho(\tau) = \frac{\sum_{m=0}^{M-1} (x[\tau+m] - \bar{x}) \cdot (h[m] - \bar{h})}{\sqrt{\sum_{m=0}^{M-1} (x[\tau+m] - \bar{x})^2} \cdot \sqrt{\sum_{m=0}^{M-1} (h[m] - \bar{h})^2}}$$

## Active Reference Templates
In our live DSP analyzer, four reference signatures run concurrently:
1. **50 Hz AC Mains Hum**: Sinusoidal template tuned to power grid frequency.
2. **60 Hz AC Mains Hum**: Alternative power grid reference.
3. **Linear Frequency Modulated (LFM) Chirp**: Simulating radar and sonar sweep pulses.
4. **Rectangular Pulse Burst**: Simulating digital packet preambles.

## Thresholding
When $\max(\rho) \ge 0.65$, the system triggers a `DETECTED` event, highlighting the UI meter in red.

[[live-dsp-browser-pipeline]]
