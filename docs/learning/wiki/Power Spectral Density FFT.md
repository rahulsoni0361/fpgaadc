[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# Power Spectral Density FFT

The **Power Spectral Density (PSD)** computed via the Fast Fourier Transform (FFT) quantifies the distribution of signal power over discrete frequency bins.

## Mathematical Formulation

Given a discrete, windowed time-domain signal $x_w[n] = x[n] \cdot w[n]$, the Real Fast Fourier Transform ($rFFT$) computes:

$$X[k] = \sum_{n=0}^{N-1} x_w[n] \cdot e^{-j 2\pi k n / N}, \quad k = 0, 1, \dots, \frac{N}{2}$$

The two-sided continuous power is normalized into single-sided Power Spectral Density:

$$P[k] = \frac{|X[k]|^2}{N \cdot \sum_{n=0}^{N-1} w^2[n]} \times 2 \quad (\text{for } 1 \le k < N/2)$$

Converting to logarithmic decibels relative to $1\text{ V RMS}$ ($\text{dBV}$):

$$\text{PSD}_{dB}[k] = 10 \log_{10}(P[k] + \epsilon)$$

## Peak Frequency Detection
By iterating over $k \ge 1$ (excluding the DC bin), the peak frequency is determined:

$$k_{peak} = \arg\max_{k \ge 1}(P[k]), \quad f_{peak} = k_{peak} \cdot \frac{F_s}{N}$$

In the live dashboard, this marker auto-locks onto the dominant frequency (e.g. ambient 50 Hz power hum) and labels it dynamically above the spectrum plot.

[[live-dsp-browser-pipeline]]
