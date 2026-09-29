# Hantek DSO5102P High-Speed Acquisition & FPGA DSP Specification

## 1. Project Objective

Integrate the **Hantek DSO5102P Digital Storage Oscilloscope** into the FPGA signal-processing and DSP stress-testing pipeline to supply real, ultra-fast **1 GSa/s** (1 Giga-sample per second) waveform data into the PYNQ-Z2 Zynq-7020 FPGA platform.

This specification defines the acquisition, extraction, and FPGA hardware datapath for high-bandwidth transients, RF pulses, and burst processing.

---

## 2. Hardware Architecture & Technical Profile

### Hantek DSO5102P Specifications

| Parameter | Specification | Engineering Implication |
| :--- | :--- | :--- |
| **Analog Bandwidth** | $100\text{ MHz}$ | Supports signals up to $100\text{ MHz}$ with $<3.5\text{ ns}$ rise time |
| **Real-Time Sample Rate** | **$1.0\text{ GSa/s}$** (Single-Channel) / $500\text{ MSa/s}$ (Dual) | $1.0\text{ ns}$ time resolution between adjacent samples |
| **Vertical Resolution** | 8-bit ($256$ discrete levels) | $1\text{ byte per sample}$ |
| **Acquisition Memory** | $24\text{ kpts}$ (standard) to $1\text{ Mpts}$ (deep memory) | $24\ \mu\text{s}$ to $1.0\text{ ms}$ real-time capture window per trigger |
| **Host Interface** | USB 2.0 Device (USB-B port on rear panel) | USBTMC / USB Bulk transfer class |
| **Effective Bus Rate** | $\sim 30\text{ to }40\text{ MB/s}$ over USB 2.0 | Full buffer transfer takes $\sim 25\text{ ms}$ to $35\text{ ms}$ |

---

## 3. System Dataflow Pipeline

Because continuous $1\text{ GSa/s}$ uncompressed stream requires $1\text{ GB/s}$ ($8\text{ Gbps}$), which exceeds USB 2.0 capacity by $25\times$, the DSO5102P operates in **Triggered Burst Frame Capture Mode**:

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                 Hantek DSO5102P Oscilloscope               │
  │                                                             │
  │  Analog Input (CH1) ──► Analog Front-End ──► 1 GSa/s Flash ADC
  │                                                   │         │
  │                                                   ▼         │
  │                                         Internal Acquisition│
  │                                            Memory (1 Mpts)  │
  └───────────────────────────────────────────────────┬─────────┘
                                                      │ USB-TMC Bulk Read
                                                      │ (~35 MB/s)
                                                      ▼
  ┌─────────────────────────────────────────────────────────────┐
  │               Host PC / PYNQ PS Orchestration               │
  │                                                             │
  │  1. Extract Raw Waveform Bytes (:WAV:DATA?)                 │
  │  2. Format into NumPy Array (8-bit signed / unsigned)       │
  │  3. Allocate DMA-safe buffer (pynq.allocate)                │
  └───────────────────────────────────────────────────┬─────────┘
                                                      │ AXI DMA (S2MM)
                                                      │ (>300 MB/s HP Port)
                                                      ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 PYNQ-Z2 FPGA Fabric (PL)                    │
  │                                                             │
  │  AXI Stream ──► Delay Line ──► Parallel DSP Blocks          │
  │                                     ├── 16x / 32x FIR       │
  │                                     ├── 1024-pt Pipelined   │
  │                                     │   FFT Engine          │
  │                                     └── Peak / RMS Detector │
  └─────────────────────────────────────────────────────────────┘
```

---

## 4. USB Communication & SCPI Control Protocol

The DSO5102P implements the standard USB Test and Measurement Class (USBTMC) and responds to standard SCPI commands:

### Primary USB Identifiers
* **Vendor ID (VID)**: `0x049F` or `0x04B4`
* **Product ID (PID)**: `0x505A` or `0x2025`
* **Protocol**: USBTMC / VISA instrument control

### Mandatory SCPI Control Sequence

1. **Identification**:
   ```text
   *IDN?  --> Returns "Hantek,DSO5102P,..."
   ```

2. **Acquisition Configuration**:
   ```text
   :ACQUIRE:TYPE NORMAL
   :ACQUIRE:NUMPOINTS 1000000        # Select 1 Mpts deep memory
   :TIMEBASE:SCALE 100NS             # Set high-speed timebase
   ```

3. **Trigger Setup**:
   ```text
   :TRIGGER:EDGE:SOURCE CH1
   :TRIGGER:EDGE:SLOPE POSITIVE
   :TRIGGER:EDGE:LEVEL 0.5V
   :SINGLE                           # Arm single-shot burst capture
   ```

4. **Waveform Readout**:
   ```text
   :WAVEFORM:SOURCE CH1
   :WAVEFORM:FORMAT BYTE
   :WAVEFORM:DATA?                   # Initiates bulk transfer of 1M samples
   ```

---

## 5. Experimental Test Progression

### Phase 1 — DSO5102P USB Enumeration & Handshake
* Connect DSO5102P rear USB-B port to Host PC / PYNQ.
* Verify USBTMC enumeration in Python using `pyvisa` / `libusb`.
* Query `*IDN?` and record scope firmware version, channel calibration, and memory options.

### Phase 2 — Raw Waveform Buffer Extraction Benchmark
* Trigger scope on a test signal (e.g. 1 kHz probe calibration square wave or floating 10 cm wire).
* Extract $N = 24,000$ and $N = 1,000,000$ points over USB.
* Measure:
  * USB transfer latency ($T_{xfer}$)
  * Data transfer throughput ($\text{MB/s}$)
  * Sample count integrity ($100\%$ zero-loss verification)

### Phase 3 — High-Speed Characterization of Captured Signals
* For each 1 GSa/s captured frame:
  * Rise time / Fall time calculation
  * Sub-nanosecond jitter analysis
  * Peak-to-Peak ($V_{pp}$), Mean ($\mu$), Standard Deviation ($\sigma$), RMS
  * 1024-point FFT spectral analysis computed on PS

### Phase 4 — High-Rate Frame Streaming to FPGA Fabric
* Pack DSO5102P raw 8-bit frames into `pynq.allocate` contiguous DMA memory.
* Trigger AXI DMA engine to burst transfer samples at $>300\text{ MB/s}$ into the PL.
* Benchmark PL reception latency and verify zero dropped samples on the AXI4-Stream interface.

### Phase 5 — FPGA DSP Saturation Experiment
* Feed 1 GSa/s captured frames into parameterized FPGA DSP blocks:
  * 16-tap to 128-tap parallel FIR filters
  * Parallel 1024-point FFT processor
  * Multi-channel DDC (Digital Down Converter)
* Compare execution speed: FPGA PL hardware vs Host PC NumPy.

---

## 6. Comparison: ADC Hardware Options in Lab

| Parameter | ADS1115 (Current) | Hantek DSO5102P | HackRF One |
| :--- | :--- | :--- | :--- |
| **Max Sample Rate** | $860\text{ Sa/s}$ | **$1,000,000,000\text{ Sa/s}$ ($1\text{ GSa/s}$)** | $20,000,000\text{ Sa/s}$ ($20\text{ MSps}$) |
| **Resolution** | 16-bit ($\Delta V = 62.5\ \mu\text{V}$) | 8-bit ($\Delta V \approx 4\text{ mV}$) | 8-bit I/Q complex |
| **Bandwidth** | DC to $\sim 400\text{ Hz}$ | **DC to $100\text{ MHz}$** | $1\text{ MHz}$ to $6\text{ GHz}$ |
| **Streaming Mode** | Continuous real-time | **Triggered Burst Buffer ($1\text{ Mpts}$)** | Continuous streaming |
| **Best Used For** | DC / Low-frequency sensor precision | Ultra-fast transients, pulses, rise-times | Wideband RF, Wi-Fi, GNSS, ISM capture |
