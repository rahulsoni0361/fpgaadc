"""
test_read_ads.py - Read 16-bit Conversion Register from ADS1115/1015 at 0x48
"""

import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

def main():
    client = PYNQAgentClient()
    code = '''
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard
import time

base = BaseOverlay('base.bit')
dev = ard.Arduino_DevMode(base.ARDUINO, ard.ARDUINO_SWCFG_DIOALL)
dev.start()

IIC_BASE = 0x40800000
REG_IISR = IIC_BASE + 0x20
REG_RESETR = IIC_BASE + 0x40
REG_CR = IIC_BASE + 0x100
REG_SR = IIC_BASE + 0x104
REG_DTR = IIC_BASE + 0x108
REG_DRR = IIC_BASE + 0x10C
REG_RFO = IIC_BASE + 0x118

def reset_bus():
    dev.write_cmd(REG_RESETR, 0x0A) # Reset core
    time.sleep(0.001)
    dev.write_cmd(REG_CR, 0x02) # TX FIFO reset
    dev.write_cmd(REG_CR, 0x01) # Enable
    dev.write_cmd(REG_IISR, 0xFF)
    time.sleep(0.001)

def write_pointer(addr, ptr_byte):
    reset_bus()
    # Dynamic mode: START + (addr << 1)
    dev.write_cmd(REG_DTR, 0x100 | ((addr << 1) & 0xFE))
    # Byte + STOP
    dev.write_cmd(REG_DTR, 0x200 | (ptr_byte & 0xFF))
    time.sleep(0.005)
    sr = dev.read_cmd(REG_SR)
    iisr = dev.read_cmd(REG_IISR)
    return sr, iisr

def write_config(addr, cfg_word):
    reset_bus()
    # START + (addr << 1)
    dev.write_cmd(REG_DTR, 0x100 | ((addr << 1) & 0xFE))
    # Pointer: 0x01 (Config Register)
    dev.write_cmd(REG_DTR, 0x01)
    # MSB
    dev.write_cmd(REG_DTR, (cfg_word >> 8) & 0xFF)
    # LSB + STOP
    dev.write_cmd(REG_DTR, 0x200 | (cfg_word & 0xFF))
    time.sleep(0.010)

def read_2bytes(addr):
    reset_bus()
    # Dynamic Read:
    # 1. START + (addr << 1) | 1 (Read)
    dev.write_cmd(REG_DTR, 0x100 | ((addr << 1) | 0x01))
    # 2. STOP + ByteCount (2 bytes)
    dev.write_cmd(REG_DTR, 0x200 | 0x02)
    time.sleep(0.010)

    # Check RX FIFO
    rfo = dev.read_cmd(REG_RFO)
    sr = dev.read_cmd(REG_SR)
    if rfo >= 1 or not (sr & 0x40): # RX FIFO not empty
        b1 = dev.read_cmd(REG_DRR) & 0xFF
        b2 = dev.read_cmd(REG_DRR) & 0xFF
        raw = (b1 << 8) | b2
        return raw, b1, b2
    return None, None, None

print("=" * 60)
print(" ADS1015 / ADS1115 READOUT VERIFICATION (0x48)")
print("=" * 60)

# Configure ADS for Single-Ended AIN0 vs GND, +/- 2.048V, continuous:
# 0xC483
print("Writing configuration: Single-Ended A0, +/- 2.048V, continuous mode...")
write_config(0x48, 0xC483)
time.sleep(0.02)

# Set pointer to Conversion Register (0x00)
print("Setting pointer to Conversion Register (0x00)...")
write_pointer(0x48, 0x00)
time.sleep(0.02)

print("\\nReading live samples:")
for i in range(10):
    raw, b1, b2 = read_2bytes(0x48)
    if raw is not None:
        if raw >= 0x8000:
            signed_val = raw - 0x10000
        else:
            signed_val = raw
        # ADS1115 16-bit: 62.5 uV/LSB
        # ADS1015 12-bit: bits 15:4, 1 mV/LSB
        v16 = signed_val * (2.048 / 32768.0)
        v12 = (signed_val >> 4) * (2.048 / 2048.0)
        print(f"  [Sample {i+1:2d}] Raw: 0x{raw:04X} (Bytes: 0x{b1:02X}, 0x{b2:02X}) | Value: {signed_val:6d} | Volt (16-bit): {v16:+.4f} V | Volt (12-bit): {v12:+.4f} V")
    else:
        print(f"  [Sample {i+1:2d}] Read timeout")
    time.sleep(0.1)

dev.stop()
print("=" * 60)
'''
    client.write_file("/home/xilinx/test_read_ads_remote.py", content=code)
    res = client.run_python("/home/xilinx", "test_read_ads_remote.py", timeout=60)
    print(res.get("stdout"))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr"))

if __name__ == "__main__":
    main()
