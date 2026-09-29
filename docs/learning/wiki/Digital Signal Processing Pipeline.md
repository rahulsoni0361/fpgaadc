[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# Digital Signal Processing Pipeline

The **Digital Signal Processing Pipeline** transforms raw, quantized voltage time-series data into actionable mathematical features and frequency spectra.

## Pipeline Processing Stages

1. **Detrending & DC Subtraction**:
   $$x_{AC}[n] = x[n] - \frac{1}{N}\sum_{i=0}^{N-1} x[i]$$
   Removes the standing $+0.293\text{ V}$ bias to prevent DC energy from overwhelming the spectrum.

2. **Time-Domain Characterization**:
   - **True RMS**: $V_{RMS} = \sqrt{\frac{1}{N}\sum x^2[n]}$
   - **Peak-to-Peak ($V_{pp}$)**: $\max(x) - \min(x)$
   - **Crest Factor**: $\frac{|V_{peak}|}{V_{RMS}}$
   - **Zero-Crossing Rate ($ZCR$)**: Counts transitions across the zero-mean threshold.

3. **Windowing**:
   Multiplying by a **Hann window** eliminates discontinuities at the buffer edges:
   $$w[n] = 0.5 - 0.5 \cos\left(\frac{2\pi n}{N}\right)$$

4. **Spectral Metrics**:
   - **Spectral Centroid**: The "center of mass" of the spectrum.
   - **Spectral Entropy ($H_{spec}$)**: Quantifies whether the signal is pure tone ($H \to 0$) or white noise ($H \to 1$).
   - **Wiener Flatness**: Ratio of geometric mean to arithmetic mean of the power spectrum.

[[live-dsp-browser-pipeline]]
