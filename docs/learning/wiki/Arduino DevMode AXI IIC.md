[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# Arduino DevMode AXI IIC

The **Arduino DevMode AXI IIC** interface provides low-latency, direct register-level access from the Processing System (PS) Python environment to the Xilinx AXI IIC IP core residing inside the MicroBlaze I/O Processor (IOP).

## Register Architecture (Base: `0x40800000`)

| Register Name | Offset | Function |
| :--- | :--- | :--- |
| **`REG_RESET`** | `0x40` | Software Reset Register (`0x0A` initiates core reset) |
| **`REG_CR`** | `0x100` | Control Register (`0x02` flushes TX FIFO, `0x01` enables core) |
| **`REG_SR`** | `0x104` | Status Register (Bit 6 = RX FIFO empty) |
| **`REG_DTR`** | `0x108` | Data Transmit FIFO (10-bit: Bit 8 = START, Bit 9 = STOP) |
| **`REG_DRR`** | `0x10C` | Data Receive FIFO |
| **`REG_RFO`** | `0x118` | RX FIFO Occupancy Register |

## Direct Hardware Control Sequence
To read from an I2C slave like the ADS1115 (`0x48`) without operating system overhead:
1. **Dynamic START & Address Byte**: Write `0x100 | (addr << 1)` to `REG_DTR`.
2. **Byte Count & STOP**: Write `0x200 | count` to `REG_DTR`.
3. **FIFO Extraction**: Poll `REG_RFO` and read incoming conversion bytes directly from `REG_DRR`.

This eliminates user-space Linux I2C driver context switching, achieving over $116\text{ Hz}$ continuous 16-bit acquisitions.

[[live-dsp-browser-pipeline]]
