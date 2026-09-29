# Live DSP Browser Pipeline: From Microvolt Wire to Browser Dashboard

> **Learning Framework:** Built using the [[Monkey Learning Framework]] to overcome the Familiarity Trap (retrieval-first learning) and networked via the [[Obsidian Knowledge Base]] specification.

---

## 1. Give the Material a Mission (Step 1)

Before reading further, anchor your mind on this single **Mission Question**:

> **"When I close this guide without looking, how do I explain how a microvolt electrical change on physical ADC pin A0 transforms into a real-time glowing oscilloscope trace and 50 Hz matched-filter detection in my web browser on port 8080?"**

Every concept, buffer, register, and thread below answers this question.

```text
 [ Physical Wire on A0 ]
          │  Analog Voltage (~0.293 V + 3 mV noise)
          ▼
 ┌────────────────────────────────────────────────────────┐
 │ 1. FPGA Embedded Hardware (Zynq-7020)                  │
 │    - CJMCU-1115 (ADS1115 16-bit Delta-Sigma ADC)       │
 │    - MicroBlaze I2C controller at AXI address 0x40800000│
 │    - [[FPGA Base Overlay]] & [[Arduino DevMode AXI IIC]]│
 └────────────────────────┬───────────────────────────────┘
                          │ Internal I2C Bus @ 100 kHz (116.4 Hz sample rate)
                          ▼
 ┌────────────────────────────────────────────────────────┐
 │ 2. FPGA Background Streaming Daemon (Port 5050)        │
 │    - [[Continuous Ring Buffer Daemon]] (FPGA Streamer) │
 │    - 4,096-sample in-memory circular deque             │
 │    - Lightweight HTTP server serving /data & /stats    │
 └────────────────────────┬───────────────────────────────┘
                          │ High-Speed LAN HTTP JSON GET (/data?n=256)
                          ▼
 ┌────────────────────────────────────────────────────────┐
 │ 3. Host Real-Time DSP Analyzer (Port 8080)             │
 │    - [[Digital Signal Processing Pipeline]]            │
 │    - Time-Domain: True RMS, Vpp, Crest Factor, ZCR     │
 │    - Freq-Domain: Hann Window + [[Power Spectral Density FFT]]
 │    - Correlation: [[Matched Filter Bank]] (cuBLAS/NumPy)
 └────────────────────────┬───────────────────────────────┘
                          │ Localhost HTTP Polling (100 ms interval)
                          ▼
 ┌────────────────────────────────────────────────────────┐
 │ 4. User Browser Dashboard (http://localhost:8080)      │
 │    - [[HTML5 Canvas Oscilloscope]] (Neon trace)        │
 │    - Real-Time Spectrum Waterfall & Frequency Marker   │
 │    - Matched-Filter Detection Progress Meters          │
 └────────────────────────────────────────────────────────┘
```

---

## 2. The Core Mechanism & Deep Dive (Step 2)

### Tier 1: Hardware Ingestion on the FPGA
When the 10 cm jumper wire on Pin A0 picks up electromagnetic energy (ambient 50 Hz AC mains hum, RF noise, or capacitive finger touch), the CJMCU-1115 converts this analog potential into 16-bit two's complement digital words. 

The Zynq-7020 does not use slow bit-banging. Instead, the [[FPGA Base Overlay]] instantiates a dedicated MicroBlaze soft processor subsystem (`iop_arduino`) connected to a hardware AXI IIC core at memory address `0x40800000`. By utilizing [[Arduino DevMode AXI IIC]], Python writes direct 32-bit control words into the hardware FIFO:
- `0x100 | slave_addr`: Hardware I2C START condition + 7-bit address.
- `0x200 | byte`: Hardware I2C STOP condition + data payload.

### Tier 2: The Continuous Ring Buffer Daemon
A critical engineering mistake in embedded web applications is querying the physical ADC synchronously when a web user requests a page. If an ADC conversion takes 8.6 ms, web requests will block, jitter, and starve the browser.

To solve this, we created the [[Continuous Ring Buffer Daemon]] (`pynq_streamer_service.py` running on the FPGA):
1. **Persistent Bitstream**: Loads `base.bit` once into FPGA fabric and keeps it hot in memory.
2. **Dedicated Ingestion Thread**: A background Python worker loops continuously, reading `ads.read_voltage()` as fast as the ADS1115 produces data ($116.4\text{ Hz}$).
3. **Thread-Safe Deque**: Samples append to a double-ended queue (`collections.deque(maxlen=4096)`).
4. **Instantaneous Slicing**: When the host queries `http://192.168.1.155:5050/data?n=256`, the daemon slices the latest 256 samples from memory in **under 2 milliseconds**.

### Tier 3: The Host DSP Engine
The script `live_dsp_analyzer.py` runs on your host workstation. Every 80 milliseconds, it polls the latest window from the FPGA and passes it through the [[Digital Signal Processing Pipeline]]:
- **DC Removal & Detrending**: Isolates the dynamic AC microvolt waveform from the static +0.293 V DC bias.
- **Windowing**: Multiplies the array by a Hann window ($w[n] = 0.5 - 0.5 \cos(2\pi n / N)$) to eliminate spectral leakage at the window boundaries.
- **Fast Fourier Transform**: Computes [[Power Spectral Density FFT]], revealing the exact frequency distribution (finding dominant peaks, spectral entropy, and Wiener flatness).
- **GPU Matched Filtering**: Executes the [[Matched Filter Bank]], computing normalized cross-correlation:
  $$\rho_{xy}(\tau) = \frac{\sum (x[n] - \bar{x})(y[n+\tau] - \bar{y})}{\|x - \bar{x}\| \|y - \bar{y}\|}$$
  This simultaneously evaluates whether the incoming noise matches a 50 Hz hum, 60 Hz hum, linear FM chirp, or radar pulse.

### Tier 4: The Browser Dashboard
When you visit `http://localhost:8080`, the browser executes pure, framework-free JavaScript:
- It polls `/api/dsp` every 100 ms via `fetch()`.
- The [[HTML5 Canvas Oscilloscope]] maps raw voltage arrays directly to canvas pixels, rendering an authentic persistence-glow phosphor oscilloscope.
- The spectrum canvas plots Power Spectral Density in dBV, rendering a dynamic gradient fill and auto-tagging the peak frequency bin in real-time.
- CSS progress bars dynamically animate the matched-filter confidence scores from 0% to 100%.

---

## 3. The "Closed-Book" Retrieval Test

> [!IMPORTANT]
> **DO NOT PEEK!** Cover the text above or look away from your screen. Answer these three questions in your own words before continuing:

1. **How would you explain the complete 4-tier pipeline simply to another engineer?**
   *(What happens at the hardware, at the FPGA daemon, at the host DSP script, and in the browser?)*
2. **What is the purpose of decoupling the ADC sampling thread from the web server using a circular ring buffer?**
   *(What catastrophic failure occurs if you query the physical I2C bus directly on every HTTP request?)*
3. **What is still unclear or surprising about this pipeline?**
   *(e.g., How does the matched filter calculate confidence, or how does the FPGA MicroBlaze FIFO work?)*

*After writing or saying your answers out loud, look back up to verify and seal any gaps in your mental model.*

---

## 4. Make One Idea "Pay Rent" (Transfer - Step 3)

Knowledge that is not applied within 24 hours evaporates. Choose **ONE** of these immediate actions:

- **Action A (Physical Probe Test):** Open `http://localhost:8080` in your browser. Physically touch the bare copper end of the 10 cm wire on Pin A0 with your finger. Watch the $V_{pp}$ leap from $3\text{ mV}$ to over $50\text{ mV}$, watch the Spectral Entropy plunge, and observe the `50 Hz AC Mains Hum` detection meter spike into the red `DETECTED` state due to capacitive body coupling.
- **Action B (Template Modification):** Open `live_dsp_analyzer.py` and modify `_generate_templates()` to add a new frequency template (e.g. 25 Hz sub-harmonic). Rerun and verify that the dashboard now monitors your custom signal signature.

---

## 5. The Cooling Gap Schedule (Step 4)

Set a calendar reminder or notification for yourself:
- **Tomorrow (24-Hour Cooling Gap):** Without opening this file or your IDE, spend 60 seconds sketching the 4-box diagram: `ADC -> Ring Buffer (5050) -> DSP FFT/Correlation (8080) -> Browser Canvas`.
- **Next Week (7-Day Cooling Gap):** Explain to yourself why the FFT reveals frequency content while the Matched Filter reveals pattern identity.
