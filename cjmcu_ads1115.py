"""
cjmcu_ads1115.py - Python Driver for CJMCU-1115 / ADS1115 on PYNQ Arduino Header
Interfaces through PYNQ Arduino Microblaze AXI IIC Controller (0x40800000).
Supports:
- Single-ended channels A0, A1, A2, A3 and Differential pairs
- Configurable Programmable Gain Amplifier (PGA) ranges
- Configurable Data Rates (8 to 860 SPS)
- Continuous and Single-shot acquisition
"""

import time
import numpy as np

class ADS1115:
    """Hardware driver for ADS1115 16-bit ADC over PYNQ Arduino Header I2C."""

    # Register pointers
    REG_CONVERSION = 0x00
    REG_CONFIG     = 0x01
    REG_LO_THRESH  = 0x02
    REG_HI_THRESH  = 0x03

    # Channels (MUX)
    MUX_DIFF_0_1 = 0x0000 # AIN0 - AIN1
    MUX_DIFF_0_3 = 0x1000 # AIN0 - AIN3
    MUX_DIFF_1_3 = 0x2000 # AIN1 - AIN3
    MUX_DIFF_2_3 = 0x3000 # AIN2 - AIN3
    MUX_SINGLE_0 = 0x4000 # AIN0 vs GND (Pin A0)
    MUX_SINGLE_1 = 0x5000 # AIN1 vs GND (Pin A1)
    MUX_SINGLE_2 = 0x6000 # AIN2 vs GND (Pin A2)
    MUX_SINGLE_3 = 0x7000 # AIN3 vs GND (Pin A3)

    # Full Scale Ranges (PGA) & LSB Voltages
    PGA_6_144V = 0x0000 # +/- 6.144 V (187.5 uV / LSB)
    PGA_4_096V = 0x0200 # +/- 4.096 V (125.0 uV / LSB)
    PGA_2_048V = 0x0400 # +/- 2.048 V (62.5 uV / LSB) - Default
    PGA_1_024V = 0x0600 # +/- 1.024 V (31.25 uV / LSB)
    PGA_0_512V = 0x0800 # +/- 0.512 V (15.625 uV / LSB)
    PGA_0_256V = 0x0A00 # +/- 0.256 V (7.8125 uV / LSB)

    # Data Rates (SPS)
    DR_8SPS   = 0x0000
    DR_16SPS  = 0x0020
    DR_32SPS  = 0x0040
    DR_64SPS  = 0x0060
    DR_128SPS = 0x0080 # Default
    DR_250SPS = 0x00A0
    DR_475SPS = 0x00C0
    DR_860SPS = 0x00E0 # Max rate for ADS1115

    # Modes
    MODE_CONTINUOUS = 0x0000
    MODE_SINGLE     = 0x0100

    def __init__(self, devmode, address=0x48):
        self.dev = devmode
        self.addr = address
        self.iic_base = 0x40800000
        self.reg_iisr = self.iic_base + 0x20
        self.reg_resetr = self.iic_base + 0x40
        self.reg_cr = self.iic_base + 0x100
        self.reg_sr = self.iic_base + 0x104
        self.reg_dtr = self.iic_base + 0x108
        self.reg_drr = self.iic_base + 0x10C
        self.reg_rfo = self.iic_base + 0x118

        self.pga = self.PGA_2_048V
        self.lsb_volts = 2.048 / 32768.0
        self.reset_bus()

    def reset_bus(self):
        """Reset AXI IIC core and flush FIFOs."""
        self.dev.write_cmd(self.reg_resetr, 0x0A)
        time.sleep(0.001)
        self.dev.write_cmd(self.reg_cr, 0x02) # TX FIFO reset
        self.dev.write_cmd(self.reg_cr, 0x01) # Enable
        self.dev.write_cmd(self.reg_iisr, 0xFF)
        time.sleep(0.001)

    def write_config(self, mux=MUX_SINGLE_0, pga=PGA_2_048V, mode=MODE_CONTINUOUS, dr=DR_128SPS):
        """Configure ADC settings."""
        self.pga = pga
        if pga == self.PGA_6_144V:
            self.lsb_volts = 6.144 / 32768.0
        elif pga == self.PGA_4_096V:
            self.lsb_volts = 4.096 / 32768.0
        elif pga == self.PGA_2_048V:
            self.lsb_volts = 2.048 / 32768.0
        elif pga == self.PGA_1_024V:
            self.lsb_volts = 1.024 / 32768.0
        elif pga == self.PGA_0_512V:
            self.lsb_volts = 0.512 / 32768.0
        elif pga == self.PGA_0_256V:
            self.lsb_volts = 0.256 / 32768.0

        # Construct 16-bit config word
        # Bit 15: OS=1 (start conversion)
        # Bits 4:0: COMP_QUE = 0b00011 (disable comparator)
        cfg = 0x8000 | mux | pga | mode | dr | 0x0003

        self.reset_bus()
        # START + Addr (W)
        self.dev.write_cmd(self.reg_dtr, 0x100 | ((self.addr << 1) & 0xFE))
        # Pointer: Config Register (0x01)
        self.dev.write_cmd(self.reg_dtr, self.REG_CONFIG)
        # MSB
        self.dev.write_cmd(self.reg_dtr, (cfg >> 8) & 0xFF)
        # LSB + STOP
        self.dev.write_cmd(self.reg_dtr, 0x200 | (cfg & 0xFF))
        time.sleep(0.010)

        # Set pointer back to Conversion Register (0x00)
        self.reset_bus()
        self.dev.write_cmd(self.reg_dtr, 0x100 | ((self.addr << 1) & 0xFE))
        self.dev.write_cmd(self.reg_dtr, 0x200 | self.REG_CONVERSION)
        time.sleep(0.005)

    def read_raw(self):
        """Read 16-bit signed raw conversion code."""
        self.reset_bus()
        # Dynamic Read 2 bytes from slave
        self.dev.write_cmd(self.reg_dtr, 0x100 | ((self.addr << 1) | 0x01))
        self.dev.write_cmd(self.reg_dtr, 0x200 | 0x02)
        time.sleep(0.005)

        rfo = self.dev.read_cmd(self.reg_rfo)
        sr = self.dev.read_cmd(self.reg_sr)
        if rfo >= 1 or not (sr & 0x40):
            msb = self.dev.read_cmd(self.reg_drr) & 0xFF
            lsb = self.dev.read_cmd(self.reg_drr) & 0xFF
            raw = (msb << 8) | lsb
            if raw >= 0x8000:
                raw -= 0x10000
            return raw
        return None

    def read_voltage(self):
        """Read voltage in Volts."""
        raw = self.read_raw()
        if raw is not None:
            return raw * self.lsb_volts
        return None
