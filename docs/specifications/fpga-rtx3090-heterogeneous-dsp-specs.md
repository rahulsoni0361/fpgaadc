# Heterogeneous Computing DSP Architecture Specification: FPGA + RTX 3090

## 1. Executive Summary & Vision

This project establishes a high-performance **heterogeneous signal-processing laboratory** coupling real-time embedded acquisition and pre-processing on the **Xilinx Zynq-7020 (PYNQ-Z2)** with massively parallel computation on an **NVIDIA GeForce RTX 3090 (24 GB GDDR6X)**.

Rather than running an artificial, synthetic GPU stress test, the RTX 3090 executes heavy, mathematically rigorous digital signal processing (DSP) and machine learning workloads that directly operate on real-time, windowed, and channelized signal streams produced by the FPGA.

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           SIGNAL SOURCES                               │
  │                                                                        │
  │   ADS1115 (16-bit I2C)       Hantek DSO5102P (1 GSa/s)     HackRF One  │
  │   Precision Sensor/Audio     Triggered Transients/RF       (20 MSps RF)│
  └─────────────────┬────────────────────────┬──────────────────────┬──────┘
                    │                        │                      │
                    ▼                        ▼                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    REAL-TIME FRONT-END: PYNQ-Z2                        │
  │                                                                        │
  │  [Programmable Logic (PL) - 220 DSP48E1 Slices, 100-200 MHz Clock]    │
  │   ├── High-Speed AXI4-Stream Ingestion & Hardware Triggering           │
  │   ├── Digital Down-Converter (DDC): NCO Mixer + CIC Decimator          │
  │   ├── Parallel Polyphase Decimation FIR Filters                        │
  │   ├── Pipelined 1024 / 4096-point Streaming FFT Engine                 │
  │   ├── Multichannel Polyphase Filter Bank (Channelizer: 8 - 256 Ch)     │
  │   └── Hardware Feature Extraction (RMS, Peak, Energy, Zero-Crossing)   │
  │                                                                        │
  │  [Processing System (PS) - Dual ARM Cortex-A9 @ 650 MHz]               │
  │   ├── AXI DMA Ring-Buffer Orchestration (HP AXI Ports >300 MB/s)       │
  │   └── High-Throughput Zero-Copy UDP / ZeroMQ Streamer                  │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Gigabit Ethernet / PCIe
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                  HEAVY COMPUTATIONAL BACK-END: RTX 3090                │
  │                                                                        │
  │  [NVIDIA RTX 3090: 10,496 CUDA Cores, 328 Tensor Cores, 24 GB VRAM]   │
  │  [Operating Target: ~200 W Sustained Thermally Controlled Benchmark]   │
  │                                                                        │
  │   ├── Option A: Real-Time High-Density Spectrogram & Spectral Entropy  │
  │   ├── Option B: Massive Matched-Filter Bank (100 to 100,000 Templates) │
  │   ├── Option C: 2D Radar Range-Doppler Pulse Compression & CFAR        │
  │   └── Option D: Deep RF Fingerprinting / Automatic Modulation Class.   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                   EXPERIMENT BENCHMARK & LIVE DASHBOARD                │
  │                                                                        │
  │   Live Waterfall / Spectrogram  │  Detection Table  │  System Telemetry│
  │   Power (W)  │  Temp (°C)  │  Latency (ms)  │  GOPS/TOPS  │  DSP Load  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Resource Profile & Compute Engine Partitioning

The architecture leverages the exact mathematical and physical strengths of each computing domain:

| Compute Domain | Hardware Platform | Physical Specialization | Primary Algorithmic Responsibilities |
| :--- | :--- | :--- | :--- |
| **Edge Acquisition / PL** | Xilinx Zynq-7020 PL (220 DSP48E1 slices, 53,200 LUTs, 4.9 Mb BRAM) | Deterministic, nanosecond-jitter streaming, sample-by-sample pipelined math | ADC ingestion, DDC, decimation, polyphase FIR, pipelined FFT, channelization, threshold triggering |
| **Host Orchestration / PS** | Dual ARM Cortex-A9 (650 MHz) / Host PC CPU | Control flow, state machine, networking, buffer management | DMA buffer ring management, socket packaging, session telemetry, flow control |
| **Massive Parallel GPU** | NVIDIA GeForce RTX 3090 (10,496 CUDA cores, 328 Tensor cores, 936 GB/s memory bandwidth) | Batched SIMD/GEMM, multidimensional FFTs, tensor operations | Massive matched-filter banks, 2D radar correlation, spectral entropy, ML modulation classification |

---

## 3. RTX 3090 Computational Workloads

### Workload 1: Massive Parallel Matched-Filter Bank (Primary Workload)

When the FPGA streams channelized RF or time-domain waveform windows $x[n]$, the RTX 3090 correlates each incoming stream against an extensive library of $K$ known templates $h_k[m]$ simultaneously:

$$C_k[n] = \sum_{m=0}^{M-1} x[n+m] \cdot h_k[m]$$

Where:
- $x$: Incoming signal window (length $N = 1024, 4096, 16384, 65536$).
- $h_k$: Signature template $k$ (chirps, barker codes, PRN codes, modulated communication preambles).
- $K$: Template bank size ($100, 1000, 10000, 100000$).

#### GPU Implementation Method:
1. **Time-Domain Batched GEMM (Matrix Multiplication)**: For short templates ($M \le 128$), formulated as $C = X \cdot H^T$ using cuBLAS Tensor Cores, maximizing arithmetic intensity.
2. **Frequency-Domain Batched cuFFT Circular Correlation**: For long templates ($M > 128$), utilizing:
   $$\mathcal{F}^{-1}\left( \mathcal{F}(X) \odot \mathcal{F}(H_k)^* \right)$$
   Precomputing and caching $\mathcal{F}(H_k)^*$ directly inside the 24 GB VRAM.

### Workload 2: High-Density Multichannel Spectrogram & Feature Extraction

The GPU continuously computes multidimensional signal intelligence features across all active channels:
- **Batched STFT (Short-Time Fourier Transform)**: 2D time-frequency waterfalls over millions of points/sec.
- **Spectral Statistics**: Spectral Centroid, Spread, Skewness, Kurtosis, Crest Factor, Flatness.
- **Spectral Entropy**:
  $$H_{spec} = -\sum_{i=1}^{B} P(f_i) \log_2 P(f_i)$$
- **Cyclostationary Spectral Analysis**: Cyclic autocorrelation function (CAF) to extract underlying symbol rates and carrier frequencies hidden beneath the noise floor.

### Workload 3: Software-Defined Radar (SDR) Range-Doppler Processing

For pulsed radar and FMCW signals:
1. **Fast-Time Processing**: Range compression via matched filtering along the ADC fast-time axis.
2. **Slow-Time Processing**: Doppler FFT across successive pulses along the slow-time axis.
3. **2D Target Detection**: 2D-CA-CFAR (Cell-Averaging Constant False Alarm Rate) adaptive noise thresholding implemented as custom CUDA kernels.

---

## 4. Parameterized Benchmark & Power Management (~200 W Limit)

### Power Optimization Philosophy
The RTX 3090 has a default factory TDP of 350 W. For this experimental laboratory, the GPU is configured to a **sustained ~200 W power ceiling** using NVIDIA Management Library (`nvidia-smi -pl 200` or NVML API).

The objective is **maximum sustained useful compute per watt** rather than thermal saturation:

```text
       ┌────────────────────────────────────────────────────────┐
       │             SUSTAINED EFFICIENCY OBJECTIVE             │
       │                                                        │
       │   Power Limit:            200 W                        │
       │   Target Utilization:     90% - 98% CUDA Compute       │
       │   VRAM Utilization:       4 GB to 16 GB                │
       │   Thermal Equilibrium:    <65°C on air/liquid cooling  │
       │   Metric of Merit:        Useful GFLOPS / Watt         │
       └────────────────────────────────────────────────────────┘
```

### Benchmark Parameter Grid

| Parameter Dimension | Sweep Range | Engineering Purpose |
| :--- | :--- | :--- |
| **Template Count ($K$)** | 100, 1,000, 10,000, 100,000 | Evaluates memory-bound vs compute-bound transitions |
| **Window Size ($N$)** | 1K, 4K, 16K, 64K samples | Evaluates FFT batching efficiency and latency trade-offs |
| **Channels** | 1, 8, 32, 128, 256 sub-bands | Stresses FPGA polyphase filter bank and GPU stream demux |
| **Precision** | FP32, FP16, INT8 (TensorRT) | Tests throughput scaling across CUDA vs Tensor cores |

### Monitored Benchmark Telemetry Matrix

1. **GPU Power Consumption**: Real-time power draw in Watts via NVML.
2. **GPU & Memory Temperature**: Thermal throttling headroom and junction temperature (°C).
3. **Compute Throughput**: Effective TeraFLOPS / Giga-Operations per second.
4. **End-to-End Latency**: Time elapsed from ADC capture $\rightarrow$ FPGA PL $\rightarrow$ ARM PS $\rightarrow$ GPU $\rightarrow$ Detection peak.
5. **FPGA DSP Utilization**: Number and percentage of active DSP48E1 slices ($/220$).
6. **FPGA Clock & Power**: PL clock frequency ($100\text{ MHz} - 200\text{ MHz}$) and estimated PL dynamic power.

---

## 5. Algorithmic Trade-off Experiment: "FPGA vs GPU Partitioning"

The fundamental scientific question of this laboratory is:

> **"At what point does an operation become more energy-efficient and lower latency in dedicated FPGA DSP slices versus a massively parallel GPU?"**

We will experimentally evaluate three architectural partitionings:

```text
CONFIG 1: FPGA-Heavy Pipeline
  ADC ──► [PL: DDC + Decimate + 256-Ch Polyphase Filter + FFT] ──► [GPU: Correlation & ML]
  - Lowest Ethernet bandwidth required
  - High FPGA DSP slice utilization (~80-95%)

CONFIG 2: Balanced Pipeline
  ADC ──► [PL: DDC + Decimate + 16-Ch FIR] ──► [GPU: FFT + Correlation + Detection]
  - Moderate FPGA resource utilization (~30-50%)
  - Balanced streaming throughput (~20-50 MB/s)

CONFIG 3: GPU-Heavy Pipeline
  ADC ──► [PL: Raw FIFO / DMA Passthrough] ──► [GPU: DDC + FIR + FFT + Correlation]
  - Minimal FPGA logic utilization (<10%)
  - Maximum GPU computational load and memory bandwidth stress
```

---

## 6. Real-World Signal Sources & Ingestion Modes

1. **Precision Baseline: Texas Instruments ADS1115 (Current Hardware)**
   - 16-bit Delta-Sigma ADC, sampled via PYNQ Arduino header I2C (`0x48`).
   - Serves as the functional, verified verification baseline for sliding-window DSP, live FFT, and GPU matched filtering.
2. **High-Speed Transients: Hantek DSO5102P (Burst Capture)**
   - Triggered 1 GSa/s single-shot captures ($1\text{ Mpts}$ buffer transferred over USB-TMC).
   - Simulates high-speed radar pulses, transient RF bursts, or high-bandwidth ultrasonic emissions.
3. **Continuous Wild RF: HackRF One (Wideband RF SDR)**
   - 1 MHz to 6 GHz RF front-end, up to 20 MSps continuous complex I/Q over USB.
   - Captures real-world, highly dynamic ambient emissions (2.4 GHz Wi-Fi / Bluetooth bursts, 433/868/915 MHz ISM packets, ADS-B 1090 MHz aircraft beacons).
