"""
scan_i2c_ads.py - Dedicated I2C Scanner & ADS1015/ADS1115 Detector for Arduino Header
Scans dedicated SCL/SDA for CJMCU-1015 / CJMCU-1115 (0x48-0x4B) and reads live A0 samples.
"""

import sys
import os
import json
import time
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

REMOTE_SCAN_CODE = '''
import time
import numpy as np
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard

# Xilinx AXI IIC register offsets on Microblaze bus
IIC_BASE = 0x40800000
REG_IISR = IIC_BASE + 0x20
REG_IIER = IIC_BASE + 0x28
REG_RESETR = IIC_BASE + 0x40
REG_CR = IIC_BASE + 0x100
REG_SR = IIC_BASE + 0x104
REG_DTR = IIC_BASE + 0x108
REG_DRR = IIC_BASE + 0x10C
REG_TFO = IIC_BASE + 0x114
REG_RFO = IIC_BASE + 0x118

CR_ENABLE = 0x01
CR_TX_FIFO_RESET = 0x02
CR_MSMS = 0x04

INTR_TX_ERROR = 0x02
INTR_TX_EMPTY = 0x04
INTR_RX_FULL = 0x08
INTR_BNB = 0x10

DYN_START = 0x100
DYN_STOP = 0x200

def reset_iic(dev):
    dev.write_cmd(REG_CR, CR_ENABLE | CR_TX_FIFO_RESET)
    time.sleep(0.001)
    dev.write_cmd(REG_CR, CR_ENABLE)
    dev.write_cmd(REG_IISR, 0xFF)

def probe_address(dev, addr_7bit):
    """Probe an I2C 7-bit address. Returns True if ACK received, False if NACK/timeout."""
    reset_iic(dev)
    
    # Send START + STOP + (addr << 1) (write probe)
    cmd = DYN_START | DYN_STOP | ((addr_7bit << 1) & 0xFE)
    dev.write_cmd(REG_DTR, cmd)
    
    ack = False
    for _ in range(100):
        iisr = dev.read_cmd(REG_IISR)
        if iisr & INTR_TX_ERROR:
            ack = False
            break
        if iisr & INTR_TX_EMPTY:
            ack = True
            break
        time.sleep(0.0001)
        
    reset_iic(dev)
    return ack

def i2c_write_reg16(dev, addr, reg, val16):
    """Write 16-bit register to I2C slave."""
    reset_iic(dev)
    # Byte 1: Start + Slave Addr (W)
    dev.write_cmd(REG_DTR, DYN_START | ((addr << 1) & 0xFE))
    # Byte 2: Register pointer
    dev.write_cmd(REG_DTR, reg & 0xFF)
    # Byte 3: MSB
    dev.write_cmd(REG_DTR, (val16 >> 8) & 0xFF)
    # Byte 4: LSB + Stop
    dev.write_cmd(REG_DTR, DYN_STOP | (val16 & 0xFF))
    time.sleep(0.005)
    reset_iic(dev)

def i2c_read_reg16(dev, addr, reg):
    """Read 16-bit register from I2C slave."""
    reset_iic(dev)
    # 1. Point to register
    dev.write_cmd(REG_DTR, DYN_START | ((addr << 1) & 0xFE))
    dev.write_cmd(REG_DTR, DYN_STOP | (reg & 0xFF))
    time.sleep(0.002)

    # 2. Repeated start to read 2 bytes
    reset_iic(dev)
    dev.write_cmd(REG_DTR, DYN_START | ((addr << 1) | 0x01)) # Read command
    dev.write_cmd(REG_DTR, DYN_STOP | 0x02) # Read 2 bytes
    time.sleep(0.010)

    # Wait for RX FIFO
    rfo = dev.read_cmd(REG_RFO)
    if rfo >= 1:
        msb = dev.read_cmd(REG_DRR) & 0xFF
        lsb = dev.read_cmd(REG_DRR) & 0xFF if dev.read_cmd(REG_RFO) >= 0 else 0
        return (msb << 8) | lsb
    return None

def main():
    print("=" * 65)
    print(" CJMCU-1015 / CJMCU-1115 (ADS1015 / ADS1115) I2C DETECTION")
    print("=" * 65)
    
    print("Loading BaseOverlay ('base.bit')...")
    base = BaseOverlay('base.bit')
    
    print("Initializing Microblaze I2C controller on Dedicated SCL/SDA pins...")
    devmode = ard.Arduino_DevMode(base.ARDUINO, ard.ARDUINO_SWCFG_DIOALL)
    devmode.start()
    reset_iic(devmode)
    
    cr = devmode.read_cmd(REG_CR)
    sr = devmode.read_cmd(REG_SR)
    print(f"Controller state: CR = 0x{cr:02X}, SR = 0x{sr:02X} (I2C Bus Ready)\\n")
    
    print("Scanning I2C Bus (Addresses 0x08 .. 0x77)...")
    found_devices = []
    for addr in range(0x08, 0x78):
        if probe_address(devmode, addr):
            found_devices.append(addr)
            info = ""
            if addr == 0x48:
                info = " <-- MATCH: ADS1015/ADS1115 (ADDR=GND)"
            elif addr == 0x49:
                info = " <-- MATCH: ADS1015/ADS1115 (ADDR=VDD)"
            elif addr == 0x4A:
                info = " <-- MATCH: ADS1015/ADS1115 (ADDR=SDA)"
            elif addr == 0x4B:
                info = " <-- MATCH: ADS1015/ADS1115 (ADDR=SCL)"
            print(f"  [ACK] Found Device at Address: 0x{addr:02X} ({addr}){info}")
            
    if not found_devices:
        print("\\n[!] No I2C ACK detected on addresses 0x08 .. 0x77.")
        print("Checking default ADS addresses specifically:")
        for a in [0x48, 0x49, 0x4A, 0x4B]:
            res = probe_address(devmode, a)
            print(f"  Probe 0x{a:02X}: {'ACK (RESPONDING!)' if res else 'NACK'}")
        devmode.stop()
        return

    # Check for ADS device
    ads_addr = None
    for a in [0x48, 0x49, 0x4A, 0x4B]:
        if a in found_devices:
            ads_addr = a
            break
            
    if ads_addr is None:
        print(f"\\nDiscovered other device(s): {[hex(a) for a in found_devices]}")
        devmode.stop()
        return

    print(f"\\n" + "=" * 65)
    print(f" DETECTED ADS1015 / ADS1115 at I2C Address: 0x{ads_addr:02X}")
    print("=" * 65)

    # 1. Read default config register (0x01)
    cfg = i2c_read_reg16(devmode, ads_addr, 0x01)
    if cfg is not None:
        print(f"Default Config Register: 0x{cfg:04X}")
    
    # 2. Configure for Single-Ended A0 (AIN0 vs GND)
    # Config word:
    # Bit 15: OS = 1 (start conversion)
    # Bits 14-12: MUX = 100 (AIN0 vs GND, single-ended)
    # Bits 11-9:  PGA = 010 (+/- 2.048V, 1 LSB = 62.5 uV for 16-bit, 1 mV for 12-bit)
    # Bit 8:      MODE = 0 (Continuous conversion mode)
    # Bits 7-5:   DR = 100 (128 SPS for ADS1115 / 1600 SPS for ADS1015)
    # Bits 4-0:   COMP = 00011 (Disable comparator)
    # Value: 0b1100_0100_1000_0011 = 0xC483
    cfg_word = 0xC483
    print(f"Configuring ADS for Single-Ended A0 continuous mode (0x{cfg_word:04X})...")
    i2c_write_reg16(devmode, ads_addr, 0x01, cfg_word)
    time.sleep(0.05)
    
    # Verify config
    cfg_read = i2c_read_reg16(devmode, ads_addr, 0x01)
    if cfg_read is not None:
        print(f"Verified Config Register: 0x{cfg_read:04X}")

    # 3. Read live samples from Conversion Register (0x00)
    print("\\nReading 10 live samples from Channel A0:")
    print("-" * 65)
    readings = []
    for i in range(10):
        raw16 = i2c_read_reg16(devmode, ads_addr, 0x00)
        if raw16 is not None:
            # ADS1115 is 16-bit signed (-32768 to +32767)
            # ADS1015 is 12-bit (bits 15:4, lower 4 bits are 0)
            if raw16 >= 0x8000:
                raw_signed = raw16 - 0x10000
            else:
                raw_signed = raw16
                
            # If lower 4 bits are consistently 0, it is 12-bit ADS1015
            # LSB voltage for +/- 2.048V FSR:
            # ADS1115 (16-bit): 2.048V / 32768 = 62.5 uV / count
            # ADS1015 (12-bit): 2.048V / 2048 = 1 mV / count
            volt_ads1115 = raw_signed * (2.048 / 32768.0)
            volt_ads1015 = (raw_signed >> 4) * (2.048 / 2048.0)
            
            readings.append(raw_signed)
            print(f"  Sample {i+1:2d}: Raw=0x{raw16:04X} ({raw_signed:6d}) | ADS1115: {volt_ads1115:.4f} V | ADS1015: {volt_ads1015:.4f} V")
        else:
            print(f"  Sample {i+1:2d}: read timeout")
        time.sleep(0.15)
        
    devmode.stop()
    print("\\n" + "=" * 65)
    print(" DETECTION SUCCESSFUL!")
    print("=" * 65)

if __name__ == '__main__':
    main()
'''

def main():
    client = PYNQAgentClient()
    print("[Host] Connecting to PYNQ board @ 192.168.1.155...")
    ping = client.ping()
    print(f"[Host] PYNQ Board Online! FPGA State: {ping.get('fpga_state')}")

    print("[Host] Uploading updated scan_i2c_ads.py...")
    client.write_file("/home/xilinx/scan_i2c_ads_remote.py", content=REMOTE_SCAN_CODE)

    print("[Host] Running ADS1015 / ADS1115 I2C Detection...")
    res = client.run_python("/home/xilinx", "scan_i2c_ads_remote.py", timeout=90)
    print("\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

if __name__ == "__main__":
    main()
