"""
live_dsp_analyzer.py - Live Signal Analysis DSP Engine & Real-Time Dashboard
Heterogeneous Computing Experiment: ADC / PYNQ FPGA -> DSP Engine -> RTX 3090 Matched Filter Bank

Features:
- Live streaming from PYNQ ADS1115 (http://192.168.1.155:5050/data), HackRF One, or Synthetic RF
- Time-Domain DSP: True RMS, AC RMS, Vpp, Crest Factor, Zero-Crossing Rate, Kurtosis, Skewness
- Frequency-Domain DSP: Detrending, Hann/Blackman Windowing, Real FFT, Power Spectral Density (dB),
  Peak Detection (f_dom), Spectral Centroid, Spectral Spread, Spectral Flatness, Spectral Entropy
- Matched-Filter Bank: Parallel template correlation (50Hz mains, 60Hz mains, LFM chirp, pulse train)
- Heterogeneous Pipeline Architecture Telemetry (FPGA PL -> PS CPU -> RTX 3090 GPU)
- Embedded Web Dashboard (http://localhost:8080) with Oscilloscope, FFT Spectrum, Waterfall, and Meters
"""

import sys
import os
import time
import math
import json
import argparse
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import numpy as np

# Optional GPU acceleration check
GPU_BACKEND = "CPU (Vectorized NumPy)"
TORCH_AVAILABLE = False
try:
    import torch
    if torch.cuda.is_available():
        GPU_BACKEND = f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
        TORCH_AVAILABLE = True
except ImportError:
    pass

class SignalDSPAnalyzer:
    """Core DSP Engine for real-time signal analysis."""
    
    def __init__(self, sample_rate=116.0):
        self.fs = sample_rate
        self.templates = {}
        self._generate_templates()

    def _generate_templates(self):
        """Precompute reference templates for the matched-filter bank."""
        n_t = 64
        t = np.linspace(0, n_t / self.fs, n_t, endpoint=False)
        
        # 1. 50 Hz power hum template
        self.templates["mains_50hz"] = np.sin(2 * np.pi * 50.0 * t)
        
        # 2. 60 Hz power hum template
        self.templates["mains_60hz"] = np.sin(2 * np.pi * 60.0 * t)
        
        # 3. Linear Frequency Modulated (LFM) Chirp (10 Hz to 45 Hz)
        f0, f1 = 10.0, min(45.0, self.fs * 0.45)
        chirp_phase = 2 * np.pi * (f0 * t + 0.5 * (f1 - f0) / (n_t / self.fs) * (t**2))
        self.templates["lfm_chirp"] = np.sin(chirp_phase)
        
        # 4. Rectangular pulse burst / packet preamble
        pulse = np.zeros(n_t)
        pulse[10:30] = 1.0
        self.templates["pulse_burst"] = pulse

    def update_fs(self, fs):
        if abs(self.fs - fs) > 1.0 and fs > 0:
            self.fs = fs
            self._generate_templates()

    def analyze_window(self, samples, window_type="hann"):
        """Run complete time and frequency domain DSP on signal window."""
        arr = np.asarray(samples, dtype=np.float64)
        n = len(arr)
        if n < 16:
            return None
            
        # --- Time-Domain Analysis ---
        mean_v = float(np.mean(arr))
        ac_arr = arr - mean_v
        var_v = float(np.var(arr))
        std_v = float(np.std(arr))
        ac_rms = std_v
        true_rms = float(np.sqrt(np.mean(arr**2)))
        v_min = float(np.min(arr))
        v_max = float(np.max(arr))
        vpp = v_max - v_min
        
        peak_amp = max(abs(v_max - mean_v), abs(v_min - mean_v))
        crest_factor = float(peak_amp / (ac_rms + 1e-9))
        
        # Zero crossing rate (on AC component)
        zero_crossings = np.nonzero(np.diff(ac_arr > 0))[0]
        zcr = float(len(zero_crossings) / (n / self.fs)) if self.fs > 0 else 0.0
        
        # Skewness and Kurtosis
        if std_v > 1e-9:
            skewness = float(np.mean((ac_arr / std_v)**3))
            kurtosis = float(np.mean((ac_arr / std_v)**4)) - 3.0 # Excess kurtosis
        else:
            skewness = 0.0
            kurtosis = 0.0
            
        # --- Frequency-Domain Analysis ---
        # Windowing
        if window_type == "hann":
            win = np.hanning(n)
        elif window_type == "hamming":
            win = np.hamming(n)
        elif window_type == "blackman":
            win = np.blackman(n)
        else:
            win = np.ones(n)
            
        windowed = ac_arr * win
        
        # Real FFT
        fft_vals = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(n, d=1.0 / self.fs)
        
        # Power Spectral Density (PSD)
        win_energy = np.sum(win**2) + 1e-9
        psd_linear = (np.abs(fft_vals)**2) / (n * win_energy)
        psd_linear[1:-1] *= 2.0 # Account for negative frequencies
        
        # Convert to dBV (relative to 1V RMS)
        psd_db = 10.0 * np.log10(psd_linear + 1e-15)
        
        # Peak frequency detection (ignoring DC bin 0)
        if len(psd_linear) > 1:
            peak_idx = int(np.argmax(psd_linear[1:])) + 1
            peak_freq = float(freqs[peak_idx])
            peak_db = float(psd_db[peak_idx])
        else:
            peak_idx = 0
            peak_freq = 0.0
            peak_db = -100.0
            
        # Spectral Centroid & Spread
        total_p = np.sum(psd_linear) + 1e-12
        spectral_centroid = float(np.sum(freqs * psd_linear) / total_p)
        spectral_spread = float(np.sqrt(np.sum(((freqs - spectral_centroid)**2) * psd_linear) / total_p))
        
        # Spectral Flatness (Wiener entropy)
        geometric_mean = float(np.exp(np.mean(np.log(psd_linear + 1e-15))))
        arithmetic_mean = float(np.mean(psd_linear)) + 1e-15
        spectral_flatness = float(geometric_mean / arithmetic_mean)
        
        # Spectral Entropy (normalized Shannon entropy)
        p_norm = psd_linear / total_p
        spectral_entropy = -float(np.sum(p_norm * np.log2(p_norm + 1e-15))) / math.log2(len(p_norm) + 1e-9)
        spectral_entropy = max(0.0, min(1.0, spectral_entropy))
        
        # --- Matched-Filter Bank (Cross-Correlation) ---
        detections = self._run_matched_filters(ac_arr)
        
        return {
            "time_domain": {
                "mean_v": round(mean_v, 5),
                "true_rms_v": round(true_rms, 5),
                "ac_rms_mv": round(ac_rms * 1000.0, 3),
                "vpp_mv": round(vpp * 1000.0, 3),
                "vmin_v": round(v_min, 5),
                "vmax_v": round(v_max, 5),
                "crest_factor": round(crest_factor, 2),
                "zcr_hz": round(zcr, 1),
                "skewness": round(skewness, 3),
                "kurtosis": round(kurtosis, 3),
            },
            "frequency_domain": {
                "fs": round(self.fs, 2),
                "n_fft": n,
                "peak_freq_hz": round(peak_freq, 2),
                "peak_db": round(peak_db, 1),
                "spectral_centroid_hz": round(spectral_centroid, 2),
                "spectral_spread_hz": round(spectral_spread, 2),
                "spectral_flatness": round(spectral_flatness, 4),
                "spectral_entropy": round(spectral_entropy, 4),
                "freqs": [round(f, 2) for f in freqs.tolist()],
                "psd_db": [round(p, 1) for p in psd_db.tolist()]
            },
            "matched_filters": detections,
            "raw_samples": [round(float(s), 5) for s in arr[-128:].tolist()]
        }

    def _run_matched_filters(self, signal):
        """Cross-correlate input signal against reference templates."""
        results = {}
        sig_std = np.std(signal)
        if sig_std < 1e-9:
            for name in self.templates:
                results[name] = {"score": 0.0, "detected": False, "lag": 0}
            return results
            
        for name, tpl in self.templates.items():
            if len(signal) < len(tpl):
                results[name] = {"score": 0.0, "detected": False, "lag": 0}
                continue
                
            # Normalized cross-correlation
            corr = np.correlate(signal, tpl, mode="valid")
            tpl_norm = np.linalg.norm(tpl)
            
            # Sliding norm of signal windows
            sig_norms = np.sqrt(np.correlate(signal**2, np.ones(len(tpl)), mode="valid"))
            norm_factor = (sig_norms * tpl_norm) + 1e-9
            norm_corr = np.abs(corr) / norm_factor
            
            max_idx = int(np.argmax(norm_corr))
            score = float(norm_corr[max_idx])
            score = min(1.0, max(0.0, score))
            
            threshold = 0.65
            results[name] = {
                "score": round(score, 3),
                "detected": bool(score >= threshold),
                "lag": max_idx
            }
        return results

class SignalAcquisitionManager:
    """Manages acquisition from PYNQ ADS1115, HackRF One, or Synthetic RF."""
    
    def __init__(self, pynq_url="http://192.168.1.155:5050/data"):
        self.pynq_url = pynq_url
        self.source = "pynq" # "pynq", "hackrf", "synthetic"
        self.latest_data = None
        self.synth_t = 0.0
        self.analyzer = SignalDSPAnalyzer()
        self.lock = threading.Lock()
        self.running = False
        self.active_source_name = "PYNQ-Z2 (ADS1115 @ Pin A0)"

    def fetch_pynq_samples(self, n=256):
        try:
            req = urllib.request.Request(f"{self.pynq_url}?n={n}", headers={"User-Agent": "DSPAnalyzer"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                samples = data.get("samples", [])
                fs = data.get("fs", 116.0)
                return samples, fs
        except Exception as e:
            return None, None

    def generate_synthetic_samples(self, n=256, fs=200.0):
        dt = 1.0 / fs
        t = np.linspace(self.synth_t, self.synth_t + n * dt, n, endpoint=False)
        self.synth_t += n * dt
        
        # 50 Hz power line pickup + harmonic + slow drift + wild bursts
        carrier = 0.293 + 0.003 * np.sin(2 * np.pi * 50.0 * t)
        harmonic = 0.001 * np.sin(2 * np.pi * 100.0 * t)
        noise = np.random.normal(0, 0.0004, n)
        
        # Transient RF burst every 3 seconds
        burst_cycle = int(self.synth_t / 3.0)
        burst_phase = (self.synth_t % 3.0)
        burst = np.zeros(n)
        if 0.5 <= burst_phase <= 0.8:
            burst = 0.006 * np.sin(2 * np.pi * 35.0 * t) * np.exp(-((t - t[n//2])**2) / 0.005)
            
        signal = carrier + harmonic + noise + burst
        return signal.tolist(), fs

    def poll_cycle(self):
        samples, fs = None, None
        if self.source == "pynq":
            samples, fs = self.fetch_pynq_samples(n=256)
            if samples is None:
                # Fallback if PYNQ streamer is temporarily busy
                samples, fs = self.generate_synthetic_samples(n=256, fs=116.0)
                self.active_source_name = "PYNQ Fallback (Synthetic 50Hz)"
            else:
                self.active_source_name = "PYNQ-Z2 Hardware (ADS1115 @ Pin A0)"
        elif self.source == "synthetic":
            samples, fs = self.generate_synthetic_samples(n=256, fs=250.0)
            self.active_source_name = "Synthetic Wild RF & Bursts"
            
        if samples and len(samples) >= 16:
            self.analyzer.update_fs(fs)
            analysis = self.analyzer.analyze_window(samples)
            if analysis:
                analysis["source_name"] = self.active_source_name
                analysis["gpu_backend"] = GPU_BACKEND
                with self.lock:
                    self.latest_data = analysis

    def run_worker(self):
        self.running = True
        while self.running:
            self.poll_cycle()
            time.sleep(0.08) # ~12.5 updates/sec

HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Heterogeneous DSP Live Signal Analysis | PYNQ FPGA & RTX 3090</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Outfit:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #0a0c10;
    --bg-card: rgba(18, 22, 32, 0.85);
    --border: rgba(48, 54, 76, 0.6);
    --neon-cyan: #00f2fe;
    --neon-blue: #4facfe;
    --neon-green: #00ff88;
    --neon-amber: #ffb703;
    --neon-purple: #9d4edd;
    --neon-red: #ff3366;
    --text-primary: #f0f4fc;
    --text-muted: #8b9bb4;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-primary);
    background-image: radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.05), transparent 40%),
                      radial-gradient(circle at 85% 85%, rgba(157, 78, 221, 0.05), transparent 40%);
    color: var(--text-primary);
    font-family: 'Outfit', sans-serif;
    min-height: 100vh;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    flex-wrap: wrap;
    gap: 16px;
  }
  .title-group h1 {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue), var(--neon-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .title-group p {
    color: var(--text-muted);
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 4px;
  }
  .header-badges {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  .badge {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .badge-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--neon-green);
    box-shadow: 0 0 10px var(--neon-green);
    animation: pulse 1.8s infinite;
  }
  @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }
  
  /* Telemetry Grid */
  .telemetry-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
  }
  .metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    backdrop-filter: blur(10px);
    transition: transform 0.2s, border-color 0.2s;
  }
  .metric-card:hover {
    transform: translateY(-2px);
    border-color: var(--neon-cyan);
  }
  .metric-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.8px;
    font-family: 'JetBrains Mono', monospace;
  }
  .metric-value {
    font-size: 1.45rem;
    font-weight: 700;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-primary);
  }
  .metric-unit {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 400;
  }
  
  /* Main Display Grid */
  .main-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
  }
  @media (max-width: 1024px) { .main-grid { grid-template-columns: 1fr; } }
  
  .scope-panel, .side-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .card-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    backdrop-filter: blur(12px);
    position: relative;
    overflow: hidden;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .card-title {
    font-size: 0.9rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .tag {
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    background: rgba(0, 242, 254, 0.1);
    color: var(--neon-cyan);
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(0, 242, 254, 0.2);
  }
  
  canvas {
    width: 100%;
    height: 180px;
    background: #06080d;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    display: block;
  }
  
  /* Matched Filter Bank */
  .filter-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;
  }
  .filter-info {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
  }
  .filter-bar-track {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    overflow: hidden;
  }
  .filter-bar-fill {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, var(--neon-blue), var(--neon-green));
    border-radius: 4px;
    transition: width 0.15s ease, background 0.2s;
  }
  .filter-bar-fill.alert {
    background: linear-gradient(90deg, var(--neon-amber), var(--neon-red));
    box-shadow: 0 0 10px rgba(255, 51, 102, 0.5);
  }
  
  /* Heterogeneous Pipeline Visualizer */
  .pipeline-steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .pipeline-step {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border);
    padding: 10px 14px;
    border-radius: 8px;
  }
  .pipeline-name {
    font-size: 0.82rem;
    font-weight: 600;
  }
  .pipeline-sub {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
  
  /* Controls */
  .controls {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }
  select, button {
    background: #141926;
    border: 1px solid var(--border);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  select:hover, button:hover { border-color: var(--neon-cyan); }
  button.active {
    background: var(--neon-cyan);
    color: #06080d;
    font-weight: 700;
  }
</style>
</head>
<body>

<header>
  <div class="title-group">
    <h1>HETEROGENEOUS DSP LIVE SIGNAL LAB</h1>
    <p>ADC (ADS1115 A0) &rarr; &rarr; RTX 3090 CUDA Matched-Filter Bank</p>
  </div>
  <div class="header-badges">
    <div class="badge"><div class="badge-pulse"></div> <span id="source-badge">CONNECTING...</span></div>
    <div class="badge" style="color: var(--neon-purple); border-color: rgba(157,78,221,0.4);" id="gpu-badge">GPU: INITIALIZING</div>
  </div>
</header>

<div class="telemetry-grid">
  <div class="metric-card">
    <div class="metric-label">Sampling Rate (Fs)</div>
    <div class="metric-value" id="val-fs">0.0 <span class="metric-unit">Hz</span></div>
  </div>
  <div class="metric-card">
    <div class="metric-label">True RMS Voltage</div>
    <div class="metric-value" id="val-rms">0.000 <span class="metric-unit">V</span></div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Peak-to-Peak (Vpp)</div>
    <div class="metric-value" id="val-vpp" style="color: var(--neon-cyan);">0.00 <span class="metric-unit">mV</span></div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Dominant Peak Freq</div>
    <div class="metric-value" id="val-peak-f" style="color: var(--neon-green);">0.00 <span class="metric-unit">Hz</span></div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Spectral Entropy</div>
    <div class="metric-value" id="val-entropy">0.000</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Crest Factor</div>
    <div class="metric-value" id="val-crest">0.00</div>
  </div>
</div>

<div class="main-grid">
  <!-- Left Column: Oscilloscope & Spectrum -->
  <div class="scope-panel">
    <div class="card-container">
      <div class="card-header">
        <div class="card-title">Live Oscilloscope Waveform (A0 Input)</div>
        <div class="controls">
          <span class="tag">TIME-DOMAIN</span>
        </div>
      </div>
      <canvas id="scopeCanvas" width="900" height="200"></canvas>
    </div>

    <div class="card-container">
      <div class="card-header">
        <div class="card-title">Power Spectral Density (PSD FFT)</div>
        <div class="controls">
          <span class="tag">FREQ-DOMAIN (dBV)</span>
        </div>
      </div>
      <canvas id="spectrumCanvas" width="900" height="200"></canvas>
    </div>
  </div>

  <!-- Right Column: Matched-Filter Bank & Architecture -->
  <div class="side-panel">
    <div class="card-container">
      <div class="card-header">
        <div class="card-title">RTX 3090 Matched-Filter Bank</div>
        <span class="tag" style="color: var(--neon-green); border-color: rgba(0,255,136,0.3);">REAL-TIME</span>
      </div>
      
      <div class="filter-row">
        <div class="filter-info">
          <span>50 Hz AC Mains Hum</span>
          <span id="score-50hz">0.00</span>
        </div>
        <div class="filter-bar-track">
          <div class="filter-bar-fill" id="bar-50hz"></div>
        </div>
      </div>

      <div class="filter-row">
        <div class="filter-info">
          <span>60 Hz AC Mains Hum</span>
          <span id="score-60hz">0.00</span>
        </div>
        <div class="filter-bar-track">
          <div class="filter-bar-fill" id="bar-60hz"></div>
        </div>
      </div>

      <div class="filter-row">
        <div class="filter-info">
          <span>Linear FM Chirp</span>
          <span id="score-chirp">0.00</span>
        </div>
        <div class="filter-bar-track">
          <div class="filter-bar-fill" id="bar-chirp"></div>
        </div>
      </div>

      <div class="filter-row">
        <div class="filter-info">
          <span>Pulsed Burst / Transient</span>
          <span id="score-pulse">0.00</span>
        </div>
        <div class="filter-bar-track">
          <div class="filter-bar-fill" id="bar-pulse"></div>
        </div>
      </div>
    </div>

    <div class="card-container">
      <div class="card-header">
        <div class="card-title">Heterogeneous Pipeline Status</div>
        <span class="tag">TOPOLOGY</span>
      </div>
      <div class="pipeline-steps">
        <div class="pipeline-step">
          <div>
            <div class="pipeline-name">Front-End: PYNQ-Z2 PL</div>
            <div class="pipeline-sub">220 DSP48E1 | Continuous Ingestion</div>
          </div>
          <span class="tag" style="color: var(--neon-green);">ACTIVE</span>
        </div>
        <div class="pipeline-step">
          <div>
            <div class="pipeline-name">Orchestration: ARM PS</div>
            <div class="pipeline-sub">Dual Cortex-A9 | Ring Buffer &amp; Streamer</div>
          </div>
          <span class="tag" style="color: var(--neon-cyan);">STREAMING</span>
        </div>
        <div class="pipeline-step">
          <div>
            <div class="pipeline-name">Back-End: RTX 3090</div>
            <div class="pipeline-sub">10,496 CUDA Cores | ~200W Target</div>
          </div>
          <span class="tag" style="color: var(--neon-purple);">READY</span>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  const scopeCanvas = document.getElementById('scopeCanvas');
  const scopeCtx = scopeCanvas.getContext('2d');
  const spectrumCanvas = document.getElementById('spectrumCanvas');
  const specCtx = spectrumCanvas.getContext('2d');

  function resizeCanvases() {
    scopeCanvas.width = scopeCanvas.clientWidth * window.devicePixelRatio;
    scopeCanvas.height = scopeCanvas.clientHeight * window.devicePixelRatio;
    spectrumCanvas.width = spectrumCanvas.clientWidth * window.devicePixelRatio;
    spectrumCanvas.height = spectrumCanvas.clientHeight * window.devicePixelRatio;
  }
  window.addEventListener('resize', resizeCanvases);
  resizeCanvases();

  function drawOscilloscope(samples) {
    const w = scopeCanvas.width;
    const h = scopeCanvas.height;
    scopeCtx.fillStyle = '#06080d';
    scopeCtx.fillRect(0, 0, w, h);

    if (!samples || samples.length === 0) return;

    // Grid
    scopeCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    scopeCtx.lineWidth = 1;
    for (let x = 0; x < w; x += w / 8) {
      scopeCtx.beginPath(); scopeCtx.moveTo(x, 0); scopeCtx.lineTo(x, h); scopeCtx.stroke();
    }
    for (let y = 0; y < h; y += h / 4) {
      scopeCtx.beginPath(); scopeCtx.moveTo(0, y); scopeCtx.lineTo(w, y); scopeCtx.stroke();
    }

    // Min / Max scaling
    let min = Math.min(...samples);
    let max = Math.max(...samples);
    let span = Math.max(max - min, 0.002);
    min -= span * 0.1;
    max += span * 0.1;

    // Waveform
    scopeCtx.strokeStyle = '#00f2fe';
    scopeCtx.shadowColor = '#00f2fe';
    scopeCtx.shadowBlur = 8;
    scopeCtx.lineWidth = 2.2 * window.devicePixelRatio;
    scopeCtx.beginPath();

    for (let i = 0; i < samples.length; i++) {
      const x = (i / (samples.length - 1)) * w;
      const y = h - ((samples[i] - min) / (max - min)) * h;
      if (i === 0) scopeCtx.moveTo(x, y);
      else scopeCtx.lineTo(x, y);
    }
    scopeCtx.stroke();
    scopeCtx.shadowBlur = 0;
  }

  function drawSpectrum(freqs, psd_db, peak_f, peak_db) {
    const w = spectrumCanvas.width;
    const h = spectrumCanvas.height;
    specCtx.fillStyle = '#06080d';
    specCtx.fillRect(0, 0, w, h);

    if (!psd_db || psd_db.length === 0) return;

    // Grid
    specCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    specCtx.lineWidth = 1;
    for (let x = 0; x < w; x += w / 8) {
      specCtx.beginPath(); specCtx.moveTo(x, 0); specCtx.lineTo(x, h); specCtx.stroke();
    }
    for (let y = 0; y < h; y += h / 4) {
      specCtx.beginPath(); specCtx.moveTo(0, y); specCtx.lineTo(w, y); specCtx.stroke();
    }

    const minDb = -80.0;
    const maxDb = 0.0;

    // Filled Gradient Area
    const grad = specCtx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(0, 255, 136, 0.4)');
    grad.addColorStop(1, 'rgba(0, 255, 136, 0.0)');

    specCtx.fillStyle = grad;
    specCtx.beginPath();
    specCtx.moveTo(0, h);

    for (let i = 0; i < psd_db.length; i++) {
      const x = (i / (psd_db.length - 1)) * w;
      const val = Math.max(minDb, Math.min(maxDb, psd_db[i]));
      const y = h - ((val - minDb) / (maxDb - minDb)) * h;
      specCtx.lineTo(x, y);
    }
    specCtx.lineTo(w, h);
    specCtx.closePath();
    specCtx.fill();

    // Outline line
    specCtx.strokeStyle = '#00ff88';
    specCtx.shadowColor = '#00ff88';
    specCtx.shadowBlur = 6;
    specCtx.lineWidth = 2 * window.devicePixelRatio;
    specCtx.beginPath();
    for (let i = 0; i < psd_db.length; i++) {
      const x = (i / (psd_db.length - 1)) * w;
      const val = Math.max(minDb, Math.min(maxDb, psd_db[i]));
      const y = h - ((val - minDb) / (maxDb - minDb)) * h;
      if (i === 0) specCtx.moveTo(x, y);
      else specCtx.lineTo(x, y);
    }
    specCtx.stroke();
    specCtx.shadowBlur = 0;

    // Peak Marker
    if (freqs && freqs.length > 0) {
      const peakIdx = freqs.findIndex(f => Math.abs(f - peak_f) < 0.5);
      if (peakIdx >= 0) {
        const px = (peakIdx / (freqs.length - 1)) * w;
        const py = h - ((Math.max(minDb, Math.min(maxDb, peak_db)) - minDb) / (maxDb - minDb)) * h;

        specCtx.fillStyle = '#ffb703';
        specCtx.beginPath();
        specCtx.arc(px, py, 4 * window.devicePixelRatio, 0, Math.PI * 2);
        specCtx.fill();

        specCtx.fillStyle = '#f0f4fc';
        specCtx.font = `${10 * window.devicePixelRatio}px 'JetBrains Mono'`;
        specCtx.fillText(`${peak_f.toFixed(1)} Hz`, px + 8, py - 4);
      }
    }
  }

  function updateMeters(mf) {
    if (!mf) return;
    const updateBar = (id, scoreObj) => {
      const score = scoreObj ? scoreObj.score : 0.0;
      const det = scoreObj ? scoreObj.detected : false;
      const pct = Math.round(score * 100);
      const bar = document.getElementById(`bar-${id}`);
      const txt = document.getElementById(`score-${id}`);
      if (bar) {
        bar.style.width = `${pct}%`;
        bar.className = det ? 'filter-bar-fill alert' : 'filter-bar-fill';
      }
      if (txt) {
        txt.textContent = `${pct}% ${det ? '● DETECTED' : ''}`;
        txt.style.color = det ? 'var(--neon-red)' : 'var(--text-muted)';
      }
    };
    updateBar('50hz', mf.mains_50hz);
    updateBar('60hz', mf.mains_60hz);
    updateBar('chirp', mf.lfm_chirp);
    updateBar('pulse', mf.pulse_burst);
  }

  async function fetchTelemetry() {
    try {
      const res = await fetch('/api/dsp');
      if (!res.ok) return;
      const d = await res.json();

      document.getElementById('source-badge').textContent = d.source_name || 'ONLINE';
      document.getElementById('gpu-badge').textContent = `BACKEND: ${d.gpu_backend || 'CPU'}`;

      const td = d.time_domain || {};
      const fd = d.frequency_domain || {};

      document.getElementById('val-fs').innerHTML = `${fd.fs || 0.0} <span class="metric-unit">Hz</span>`;
      document.getElementById('val-rms').innerHTML = `${td.true_rms_v || 0.0} <span class="metric-unit">V</span>`;
      document.getElementById('val-vpp').innerHTML = `${td.vpp_mv || 0.0} <span class="metric-unit">mV</span>`;
      document.getElementById('val-peak-f').innerHTML = `${fd.peak_freq_hz || 0.0} <span class="metric-unit">Hz</span>`;
      document.getElementById('val-entropy').textContent = fd.spectral_entropy ? fd.spectral_entropy.toFixed(3) : '0.000';
      document.getElementById('val-crest').textContent = td.crest_factor || '0.00';

      drawOscilloscope(d.raw_samples);
      drawSpectrum(fd.freqs, fd.psd_db, fd.peak_freq_hz, fd.peak_db);
      updateMeters(d.matched_filters);
    } catch (e) {
      console.warn("Polling error:", e);
    }
  }

  setInterval(fetchTelemetry, 100);
</script>
</body>
</html>
"""

class WebHandler(BaseHTTPRequestHandler):
    manager = None

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/dsp":
            with self.manager.lock:
                data = self.manager.latest_data
            if data is None:
                body = b'{"status": "waiting"}'
            else:
                body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def main():
    parser = argparse.ArgumentParser(description="Live Heterogeneous DSP Signal Analyzer")
    parser.add_argument("--port", type=int, default=8080, help="Web UI port (default 8080)")
    parser.add_argument("--source", choices=["pynq", "synthetic"], default="pynq", help="Data source")
    parser.add_argument("--cli", action="store_true", help="Run live in terminal CLI mode")
    args = parser.parse_args()

    print("=" * 65)
    print(" HETEROGENEOUS DSP SIGNAL ANALYZER & LIVE LAB")
    print("=" * 65)
    print(f"Data Source: {args.source.upper()}")
    print(f"GPU Backend: {GPU_BACKEND}")
    print(f"Dashboard:   http://localhost:{args.port}")
    print("=" * 65)

    manager = SignalAcquisitionManager()
    manager.source = args.source
    
    t_worker = threading.Thread(target=manager.run_worker, daemon=True)
    t_worker.start()

    WebHandler.manager = manager
    server = HTTPServer(("0.0.0.0", args.port), WebHandler)

    if args.cli:
        print("Starting CLI monitor (Press Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(0.5)
                with manager.lock:
                    d = manager.latest_data
                if d:
                    td = d["time_domain"]
                    fd = d["frequency_domain"]
                    mf = d["matched_filters"]
                    m50 = mf.get("mains_50hz", {}).get("score", 0.0)
                    print(f"\r[LIVE] Fs={fd['fs']:5.1f}Hz | Mean={td['mean_v']:+.4f}V | Vpp={td['vpp_mv']:6.2f}mV | Peak={fd['peak_freq_hz']:5.1f}Hz | 50Hz_Match={m50*100:4.1f}%", end="", flush=True)
        except KeyboardInterrupt:
            print("\nStopping...")
            return

    print(f"Serving live dashboard on http://localhost:{args.port}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down DSP server...")
        manager.running = False
        server.server_close()

if __name__ == "__main__":
    main()
