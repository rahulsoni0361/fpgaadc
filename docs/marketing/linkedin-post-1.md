Most browser telemetry demos show pre-recorded mock data. 

I wanted reality.

Here is a physical experiment I performed: streaming continuous microvolts from a 10 cm wire into an FPGA, running real-time DSP, and rendering an oscilloscope-like display in the browser at 60 FPS with zero frameworks.

THE DATAFLOW:

10 cm Wire (Pin A0)
  │ Microvolt ambient EMI / 50 Hz pickup
  ▼
FPGA Hardware Ingestion (Zynq-7020)
  │ MicroBlaze AXI IIC core @ 0x40800000 (116.4 Sa/s)
  ▼
Decoupled Ring Buffer Daemon
  │ 4,096-sample queue (<150 µs slice latency)
  ▼
Host DSP & Matched-Filter Engine
  │ Hann window + Real FFT Power Spectral Density
  │ Spectral Entropy + Cross-Correlation Bank
  ▼
HTML5 Canvas Browser Interface
  • Oscilloscope-like phosphor persistence waveform
  • Dynamic PSD waterfall with locked 50 Hz peak
  • Real-time template detection meters (0 - 100%)

3 LESSONS I LEARNED:

1. Never Query Hardware Synchronously on HTTP Requests
Querying the physical I2C bus on web requests caused bus contention and dropped frames. I built an in-memory ring-buffer daemon that samples the ADC uninterrupted, slicing 256 samples from RAM in under 150 microseconds.

2. True DSP Over Raw Numbers
Showing raw voltage tells you nothing. In my DSP engine, I compute True RMS, Peak-to-Peak (subtle 2.7 mV noise), and Spectral Entropy—proving whether energy is structured mains hum or thermal noise.

3. Real-Time Matched-Filter Detection
Instead of crude thresholding, I cross-correlate incoming frames against mathematical signatures. What I found intriguing was pulsed bursts: even when the raw waveform looks completely flat, the matched filter pulls transient switching bursts right out of the noise floor.

WHAT I AM BUILDING NEXT:
Scaling into my 200W Heterogeneous Computing Lab:
ADC Front-End → FPGA Fabric (DDC, FIR, FFT) → RTX 3090 GPU (100k Matched-Filter Bank).

How do you handle hardware-to-browser buffering in edge telemetry?

Source code and pulsed burst notes in the first comment. 👇

#FPGA #EmbeddedSystems #SignalProcessing #DSP #Xilinx #Oscilloscope #RealTime #Python #CUDA

---

FIRST COMMENT (Copy & paste as the first comment on your post):

Here is the breakdown of why pulsed bursts were the most intriguing part of this experiment:

In the time-domain oscilloscope view, the 10 cm wire looks like it's just idling in steady 2.7 mV RMS ambient noise. To the naked eye, it looks completely dead.

Yet every few seconds, the "Pulsed Burst" matched-filter correlation meter abruptly spikes.

Why? 

Because a matched filter doesn't care about instantaneous voltage amplitude. It computes the normalized cross-correlation against a known impulse signature.

When nearby switch-mode power converters or ambient RF emitters leak microsecond transient ringing, the raw waveform barely ripples above the noise floor. But in the correlation domain, that coherent energy integrates constructively, punching right through the stochastic thermal noise.

It's a textbook demonstration of processing gain in action.

Full architectural specs and hardware driver files:
https://github.com/.../fpgaadc
