[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# FPGA Base Overlay

The **FPGA Base Overlay** is the foundational bitstream architecture programmed into the Programmable Logic (PL) of the Zynq-7020 chip.

## Architectural Role in the Pipeline
Rather than requiring custom HDL compilation for every preliminary test, the base overlay instantiates pre-synthesized hardware accelerator subsystems:
- **`iop_arduino`**: A MicroBlaze 32-bit soft processor dedicated to the Arduino header.
- **Hardware AXI IIC Core**: Instantiated at base address `0x40800000`, connected directly to the dedicated I2C pins (SCL/SDA next to AREF).
- **AXI DMA Engines**: High-performance streaming channels connected to the PS High-Performance (HP) DDR memory ports.

## Persistent In-Memory Loading
Loading a bitstream over the Processor Configuration Access Port (PCAP) takes 5 to 8 seconds. In the live streaming architecture, the base overlay is instantiated **once** upon service launch and kept resident:

```python
from pynq.overlays.base import BaseOverlay
base = BaseOverlay('base.bit')
```

This ensures zero reconfiguration overhead during live streaming operations.

[[live-dsp-browser-pipeline]]
