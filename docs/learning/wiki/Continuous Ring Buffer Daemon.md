[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# Continuous Ring Buffer Daemon

The **Continuous Ring Buffer Daemon** (`pynq_streamer_service.py`) acts as the high-speed decoupling layer between physical hardware sampling and remote network consumers.

## The Decoupling Problem
Directly reading an ADC upon each HTTP request introduces severe performance degradation:
- I2C transaction latency ($8.6\text{ ms}$) blocks the web server.
- High-frequency web polling creates bus contention and drops ADC samples.
- Signal history is lost between discrete HTTP requests.

## Architecture and Threading Model

```text
 ┌─────────────────────────────────────────────────────────┐
 │ Background Ingestion Thread (116.4 Hz Continuous)       │
 │   while running:                                        │
 │     voltage = ads.read_voltage()                        │
 │     deque.append(voltage)   [Capacity: 4,096 samples]   │
 └────────────────────────────┬────────────────────────────┘
                              │ Thread-safe Lock
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Lightweight HTTP Server Thread (Port 5050)              │
 │   GET /data?n=256  ──► Slice latest 256 samples (<2 ms) │
 │   GET /stats       ──► Return Vpp, RMS, and Fs metrics  │
 └─────────────────────────────────────────────────────────┘
```

## Benefits
1. **Zero Sample Loss**: The ADC runs uninterrupted at its hardware conversion limit.
2. **Sub-2ms Latency**: Slicing the latest $N$ samples from a Python `deque` takes less than $100\ \mu\text{s}$.
3. **Multi-Client Isolation**: Multiple analyzers or dashboards can monitor the same physical signal concurrently.

[[live-dsp-browser-pipeline]]
