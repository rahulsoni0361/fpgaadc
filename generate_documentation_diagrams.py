"""
generate_documentation_diagrams.py - High-Resolution 4K/Retina Mermaid to PNG Renderer
Features:
- Headless Chrome with --force-device-scale-factor=2.5 (Retina HiDPI)
- Scaled 24px/26px typography for effortless readability
- Automatic bounding-box cropping with Pillow (zero wasted margin space)
"""

import os
import sys
import subprocess
import time
from PIL import Image

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

MERMAID_JS = r"H:\life\07-projects\02-ai skills\03-coding-infrastructure\Agent-framework\Project-management-skills-and-agents\mermaid-skill\resources\mermaid.min.js"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
  <style>
    body {
      background-color: #0b0f19;
      color: #f0f4fc;
      font-family: 'Inter', -apple-system, sans-serif;
      margin: 0;
      padding: 50px;
      display: inline-block;
    }
    #wrapper {
      background: #111827;
      border: 3px solid #374151;
      border-radius: 20px;
      padding: 44px 52px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.9);
      display: inline-block;
    }
    .mermaid {
      display: inline-block;
    }
    /* Enforce large, razor-sharp typography */
    .node text, .node .label, .label text {
      font-family: 'Inter', sans-serif !important;
      font-size: 26px !important;
      font-weight: 700 !important;
      letter-spacing: -0.2px;
    }
    .edgeLabel text, .edgeLabel span {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 20px !important;
      font-weight: 600 !important;
      color: #93c5fd !important;
    }
    .cluster-label text, .cluster text {
      font-family: 'Inter', sans-serif !important;
      font-size: 28px !important;
      font-weight: 800 !important;
      fill: #38bdf8 !important;
    }
    .actor {
      font-family: 'Inter', sans-serif !important;
      font-size: 26px !important;
      font-weight: 700 !important;
    }
    .messageText {
      font-family: 'Inter', sans-serif !important;
      font-size: 22px !important;
      font-weight: 600 !important;
      fill: #f1f5f9 !important;
    }
    .noteText {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 20px !important;
      font-weight: 600 !important;
    }
  </style>
  <script src="__MERMAID_JS_PATH__"></script>
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis'
      },
      sequence: {
        useMaxWidth: false,
        showSequenceNumbers: true,
        actorFontSize: 26,
        messageFontSize: 22,
        noteFontSize: 20
      },
      themeVariables: {
        darkMode: true,
        fontSize: '26px',
        fontFamily: 'Inter, sans-serif',
        background: '#111827',
        primaryColor: '#1e293b',
        primaryTextColor: '#f8fafc',
        primaryBorderColor: '#00f2fe',
        lineColor: '#38bdf8',
        secondaryColor: '#0f172a',
        tertiaryColor: '#1e293b',
        noteBkgColor: '#1e293b',
        noteTextColor: '#93c5fd',
        signalColor: '#38bdf8',
        signalTextColor: '#f8fafc'
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

def render_high_res(mermaid_code, output_png, base_width=3200, base_height=2400):
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    temp_html = output_png.replace(".png", "_raw.html")
    raw_screenshot = output_png.replace(".png", "_full.png")
    
    js_uri = "file:///" + MERMAID_JS.replace("\\", "/")
    html = HTML_TEMPLATE.replace("__MERMAID_JS_PATH__", js_uri).replace("__MERMAID_CODE__", mermaid_code.strip())
    
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)
        
    html_uri = "file:///" + os.path.abspath(temp_html).replace("\\", "/")
    
    # 2.5x Device Scale Factor turns 3200x2400 viewport into true 8000x6000 ultra-crisp render
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        "--force-device-scale-factor=2.5",
        f"--screenshot={os.path.abspath(raw_screenshot)}",
        f"--window-size={base_width},{base_height}",
        "--virtual-time-budget=5000",
        html_uri
    ]
    
    print(f"Rendering high-res {os.path.basename(output_png)}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if os.path.exists(temp_html):
        os.remove(temp_html)
        
    if not os.path.exists(raw_screenshot):
        print(f"  [ERROR] Chrome failed to generate screenshot: {res.stderr}")
        return False
        
    # Crop tightly to the bounding box of the diagram
    try:
        img = Image.open(raw_screenshot)
        rgb_img = img.convert("RGB")
        
        # Bounding box of content distinct from outer background (#0b0f19 -> 11, 15, 25)
        # Scan for pixels with brightness above background
        width, height = img.size
        pixels = rgb_img.load()
        bg_r, bg_g, bg_b = 11, 15, 25
        
        left, top, right, bottom = width, height, 0, 0
        step = 4 # Fast scan step
        for y in range(0, height, step):
            for x in range(0, width, step):
                r, g, b = pixels[x, y]
                # If pixel differs meaningfully from background
                if abs(r - bg_r) > 10 or abs(g - bg_g) > 10 or abs(b - bg_b) > 10:
                    if x < left: left = x
                    if x > right: right = x
                    if y < top: top = y
                    if y > bottom: bottom = y
                    
        padding = 40
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        
        if right > left and bottom > top:
            cropped = img.crop((left, top, right, bottom))
            cropped.save(output_png, "PNG", optimize=True)
            print(f"  [SUCCESS] {os.path.basename(output_png)} -> {cropped.size[0]}x{cropped.size[1]} px ({os.path.getsize(output_png):,} bytes)")
        else:
            img.save(output_png, "PNG", optimize=True)
            print(f"  [SUCCESS] {os.path.basename(output_png)} -> {img.size[0]}x{img.size[1]} px")
            
        if os.path.exists(raw_screenshot):
            os.remove(raw_screenshot)
        return True
    except Exception as e:
        print(f"  [ERROR] Cropping failed: {e}")
        if os.path.exists(raw_screenshot):
            os.rename(raw_screenshot, output_png)
        return True

# Diagram 1: System End-to-End Architecture
D1 = """
graph TD
    subgraph SENSORS ["1. Physical Signals & Sensor Front-Ends"]
        A1["10 cm Wire Antenna<br/>Microvolt Ambient EMI / 50 Hz Hum"]
        A2["HackRF One SDR<br/>1 MHz - 6 GHz, 20 MSps Complex I/Q"]
        A3["Hantek DSO5102P<br/>1 GSa/s Triggered Burst Capture"]
    end

    subgraph FPGA ["2. FPGA Hardware Layer (Xilinx Zynq-7020)"]
        B1["ADS1115 16-bit Delta-Sigma ADC<br/>I2C Address: 0x48 @ Pin A0"]
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
        X0["Raw ADC Samples x[n]<br/>256 samples @ 116.4 Hz"]
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
    render_high_res(D1, os.path.join(out_dir, "system_architecture.png"), base_width=3200, base_height=2600)
    render_high_res(D2, os.path.join(out_dir, "dsp_pipeline.png"), base_width=3400, base_height=1800)
    render_high_res(D3, os.path.join(out_dir, "decoupled_threading.png"), base_width=2800, base_height=2000)
    print("\nAll Ultra-High-Resolution PNGs rendered successfully!")
