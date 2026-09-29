"""
generate_documentation_diagrams.py - Generate High-Resolution Architecture PNGs
Renders Mermaid charts to standalone PNGs in the documentation/ folder.
"""

import os
import sys
import subprocess

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

MERMAID_JS = r"H:\life\07-projects\02-ai skills\03-coding-infrastructure\Agent-framework\Project-management-skills-and-agents\mermaid-skill\resources\mermaid.min.js"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      background-color: #0b0f19;
      color: #f0f4fc;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 40px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      box-sizing: border-box;
    }
    #wrapper {
      background: #111827;
      border: 1px solid #374151;
      border-radius: 16px;
      padding: 36px 44px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
      display: inline-block;
    }
    .mermaid {
      display: flex;
      justify-content: center;
    }
  </style>
  <script src="__MERMAID_JS_PATH__"></script>
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#111827',
        primaryColor: '#1f2937',
        primaryTextColor: '#f9fafb',
        primaryBorderColor: '#00f2fe',
        lineColor: '#38bdf8',
        secondaryColor: '#0f172a',
        tertiaryColor: '#1f2937',
        noteBkgColor: '#1e293b',
        noteTextColor: '#93c5fd'
      }
    });
  </script>
</head>
<body>
  <div id="wrapper">
    <div class="mermaid">
__MERMAID_CODE__
    </div>
  </div>
</body>
</html>
"""

def render(mermaid_code, output_png, width=1800, height=1200):
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    temp_html = output_png.replace(".png", "_tmp.html")
    
    js_uri = "file:///" + MERMAID_JS.replace("\\", "/")
    html = HTML_TEMPLATE.replace("__MERMAID_JS_PATH__", js_uri).replace("__MERMAID_CODE__", mermaid_code.strip())
    
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)
        
    html_uri = "file:///" + os.path.abspath(temp_html).replace("\\", "/")
    
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        f"--screenshot={os.path.abspath(output_png)}",
        f"--window-size={width},{height}",
        "--virtual-time-budget=4000",
        html_uri
    ]
    
    print(f"Rendering {os.path.basename(output_png)}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    
    if os.path.exists(temp_html):
        os.remove(temp_html)
        
    if os.path.exists(output_png) and os.path.getsize(output_png) > 1000:
        print(f"  [DONE] {os.path.basename(output_png)} ({os.path.getsize(output_png):,} bytes)")
        return True
    else:
        print(f"  [FAIL] Failed: {res.stderr}")
        return False

# Diagram 1: System End-to-End Architecture
D1 = """
graph TD
    subgraph SENSORS ["1. Physical Signals & Sensor Front-Ends"]
        A1["10 cm Wire Antenna<br/>(Microvolt Ambient EMI / 50 Hz Hum)"]
        A2["HackRF One SDR<br/>(1 MHz - 6 GHz, 20 MSps Complex I/Q)"]
        A3["Hantek DSO5102P<br/>(1 GSa/s Triggered Burst Capture)"]
    end

    subgraph FPGA ["2. FPGA Hardware Layer (Xilinx Zynq-7020)"]
        B1["ADS1115 16-bit Delta-Sigma ADC<br/>(I2C Address: 0x48 @ Pin A0)"]
        B2["Programmable Logic (PL Fabric)<br/>220 DSP48E1 Slices | MicroBlaze IOP Subsystem"]
        B3["AXI IIC Hardware Core<br/>Base Address: 0x40800000"]
        B4["ARM Cortex-A9 Processing System (PS)<br/>Direct Register Control via Arduino DevMode"]
        B1 -->|I2C SCL/SDA| B3
        B3 <--> B2
        B2 <--> B4
    end

    subgraph DAEMON ["3. In-Memory Streaming Daemon (Port 5050)"]
        C1["Continuous Hardware Ingestion Thread<br/>116.4 Sa/s Uninterrupted Background Sampling"]
        C2[("4,096-Sample Circular Deque<br/>RAM Buffer (<150 us Slice Latency)")]
        C3["Lightweight HTTP REST Server (Port 5050)<br/>Endpoints: /data, /stats, /ping"]
        C1 -->|Append Float32| C2
        C2 -->|Zero-Copy Slicing| C3
    end

    subgraph HOST_DSP ["4. Host Real-Time DSP Engine (Port 8080)"]
        D1["Sliding Window Ingestion<br/>256-sample frames @ 12.5 Hz"]
        D2["Time-Domain Characterization<br/>True RMS, Vpp, Crest Factor, Zero-Crossing"]
        D3["Power Spectral Density FFT<br/>Hann Window + rFFT + Dominant Peak Locking"]
        D4["Parallel Matched-Filter Bank<br/>50Hz, 60Hz, LFM Chirp, Pulsed Burst"]
        D1 --> D2
        D1 --> D3
        D1 --> D4
    end

    subgraph PRESENTATION ["5. Browser UI & Heterogeneous GPU Compute"]
        E1["HTML5 Canvas Oscilloscope<br/>60 FPS Phosphor-Glow Persistence Trace"]
        E2["Real-Time Spectrum Waterfall<br/>Dynamic Power Heatmap & Peak Tag"]
        E3["Confidence Meters<br/>Detection Status (0 - 100%)"]
        E4["NVIDIA RTX 3090 GPU (Heterogeneous Back-End)<br/>100k Matched Filters @ ~200W Sustained Power"]
    end

    A1 --> B1
    A2 -.-> D1
    A3 -.-> D1
    B4 --> C1
    C3 -->|HTTP LAN JSON| D1
    D2 --> E1
    D3 --> E2
    D4 --> E3
    D4 -.-> E4
"""

# Diagram 2: Detailed DSP Signal Processing Pipeline
D2 = """
graph LR
    subgraph INPUT ["Raw Ingestion"]
        X0["Raw ADC Samples x[n]<br/>(256 samples @ 116.4 Hz)"]
    end

    subgraph TIME_DSP ["1. Time-Domain Processing"]
        T1["DC Removal & Detrending<br/>x_ac = x - mean(x)"]
        T2["True RMS & Peak-to-Peak<br/>Vrms = sqrt(mean(x^2)), Vpp = max - min"]
        T3["Crest Factor & Zero Crossing<br/>Vpeak / Vrms Ratio & ZCR Frequency"]
        X0 --> T1
        T1 --> T2
        T1 --> T3
    end

    subgraph FREQ_DSP ["2. Frequency-Domain Processing"]
        F1["Hann Windowing<br/>w[n] = 0.5 - 0.5*cos(2*pi*n/N)"]
        F2["Real FFT (rFFT)<br/>X[k] = FFT(x_ac * w)"]
        F3["Power Spectral Density (PSD)<br/>PSD_dB = 10*log10(|X[k]|^2 / Norm)"]
        F4["Spectral Feature Extraction<br/>Dominant Peak, Centroid, Flatness, Entropy"]
        T1 --> F1
        F1 --> F2
        F2 --> F3
        F3 --> F4
    end

    subgraph MATCHED_FILTER ["3. Matched-Filter Bank"]
        M1["Template Library h_k[m]<br/>50Hz Hum, 60Hz Hum, LFM Chirp, Pulse"]
        M2["Normalized Cross-Correlation<br/>rho(tau) = Conv(x_ac, h_k) / (||x||*||h||)"]
        M3["Peak Detector & Threshold<br/>Score = max(|rho|) >= 0.65"]
        M4{"Event Detection?<br/>Confidence 0 - 100%"}
        T1 --> M2
        M1 --> M2
        M2 --> M3
        M3 --> M4
    end
"""

# Diagram 3: Decoupled Multi-Tier Threading & Sequence Model
D3 = """
sequenceDiagram
    autonumber
    actor ADC as Physical ADC (ADS1115)
    participant HW_THREAD as FPGA Ingestion Thread
    participant RING_BUF as 4096-Sample Circular Deque
    participant HTTP_SRV as Streamer HTTP Server (:5050)
    participant DSP_HOST as Host DSP Engine (:8080)
    participant BROWSER as Browser Dashboard (HTML5)

    Note over ADC,RING_BUF: Tier 1: Hardware Ingestion Loop (116.4 Hz Continuous)
    loop Continuous Hardware Sampling
        HW_THREAD->>ADC: Direct AXI IIC read_voltage()
        ADC-->>HW_THREAD: 16-bit Voltage Sample (0.293V + noise)
        HW_THREAD->>RING_BUF: append(sample) [Thread-Safe Lock]
    end

    Note over HTTP_SRV,DSP_HOST: Tier 2: Host DSP Polling Loop (12.5 Hz / 80ms)
    loop Every 80 ms
        DSP_HOST->>HTTP_SRV: GET /data?n=256
        HTTP_SRV->>RING_BUF: Slice latest 256 samples (<150 us)
        RING_BUF-->>HTTP_SRV: [v0, v1, ..., v255] + Fs
        HTTP_SRV-->>DSP_HOST: JSON Payload (Samples, Fs, Timestamps)
        Note over DSP_HOST: Compute FFT, PSD, Entropy, Matched Filters
    end

    Note over DSP_HOST,BROWSER: Tier 3: Browser UI Polling Loop (10 Hz / 100ms)
    loop Every 100 ms
        BROWSER->>DSP_HOST: GET /api/dsp
        DSP_HOST-->>BROWSER: JSON (Waveform, Spectrum, Metrics, Filter Scores)
        Note over BROWSER: Render Canvas Oscilloscope (60 FPS) & Waterfall
    end
"""

if __name__ == "__main__":
    out_dir = r"h:\07-projects\03-inhouse-projects\fpgaadc\documentation"
    render(D1, os.path.join(out_dir, "system_architecture.png"), width=1800, height=1350)
    render(D2, os.path.join(out_dir, "dsp_pipeline.png"), width=1800, height=1100)
    render(D3, os.path.join(out_dir, "decoupled_threading.png"), width=1600, height=1200)
    print("\nAll diagrams successfully generated in:", out_dir)
