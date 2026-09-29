"""
probe_i2c_pins.py - Diagnostic tool to inspect logic levels across all Arduino header pins
and test I2C communication on A4/A5, Dedicated, and other pin pairs.
"""

import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

REMOTE_PROBE_CODE = '''
import time
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard

print("=" * 65)
print(" ARDUINO HEADER PIN LOGIC LEVEL & I2C DETECTOR")
print("=" * 65)

base = BaseOverlay('base.bit')

# Pin names: 0..13 = D0..D13, 14..19 = A0..A5
pin_names = [f"D{i}" for i in range(14)] + [f"A{i}" for i in range(6)]

# Initialize DevMode with all pins configured as inputs (GPIO mode)
# ARDUINO_SWCFG_DIOALL configures all 20 pins as GPIO
devmode = ard.Arduino_DevMode(base.ARDUINO, ard.ARDUINO_SWCFG_DIOALL)
devmode.start()

# Read tri-state register and set all 20 pins as inputs (1 = input)
# DIO_TRI offset is 0x4, DIO_DATA offset is 0x0
DIO_BASE = ard.ARDUINO_DIO_BASEADDR # 0x40020000
devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, 0x000FFFFF) # all 20 pins input

# Read logic levels
raw_data = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET)
pin_states = [(raw_data >> i) & 1 for i in range(20)]

print("\\n1. Current Logic Level on Arduino Header Pins (1 = HIGH / ~3.3V, 0 = LOW):")
print("-" * 65)
for i in range(20):
    state_str = "HIGH (Pull-up detected!)" if pin_states[i] == 1 else "LOW / GND"
    print(f"  Pin {i:2d} ({pin_names[i]:>3s}): {state_str}")

high_pins = [i for i in range(20) if pin_states[i] == 1]
print(f"\\nPins currently HIGH: {[pin_names[p] for p in high_pins]}")

# -----------------------------------------------------------------
# 2. Bit-banged I2C probe function
# -----------------------------------------------------------------
def bb_i2c_probe(sda_pin, scl_pin, target_addr=0x48):
    """Simple software bit-bang I2C probe on any pair of pins."""
    # Helpers
    def set_scl(val):
        tri = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET)
        if val == 1:
            # Input mode (pulled high by resistor)
            tri |= (1 << scl_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, tri)
        else:
            # Output LOW
            data = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET)
            data &= ~(1 << scl_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET, data)
            tri &= ~(1 << scl_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, tri)

    def set_sda(val):
        tri = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET)
        if val == 1:
            tri |= (1 << sda_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, tri)
        else:
            data = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET)
            data &= ~(1 << sda_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET, data)
            tri &= ~(1 << sda_pin)
            devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, tri)

    def get_sda():
        tri = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET)
        tri |= (1 << sda_pin)
        devmode.write_cmd(DIO_BASE + ard.ARDUINO_DIO_TRI_OFFSET, tri)
        data = devmode.read_cmd(DIO_BASE + ard.ARDUINO_DIO_DATA_OFFSET)
        return (data >> sda_pin) & 1

    # Start condition
    set_sda(1); set_scl(1); time.sleep(0.001)
    set_sda(0); time.sleep(0.001)
    set_scl(0); time.sleep(0.001)

    # Send address byte (addr << 1) | 0
    addr_byte = (target_addr << 1) & 0xFE
    for bit in range(7, -1, -1):
        b = (addr_byte >> bit) & 1
        set_sda(b); time.sleep(0.0005)
        set_scl(1); time.sleep(0.0005)
        set_scl(0); time.sleep(0.0005)

    # Read ACK
    set_sda(1) # release SDA
    time.sleep(0.0005)
    set_scl(1)
    time.sleep(0.0005)
    ack_val = get_sda()
    set_scl(0)
    time.sleep(0.0005)

    # Stop condition
    set_sda(0); time.sleep(0.0005)
    set_scl(1); time.sleep(0.0005)
    set_sda(1); time.sleep(0.0005)

    return (ack_val == 0) # 0 means ACK!

# Test common pairs:
candidate_pairs = [
    (18, 19, "A4=SDA, A5=SCL (Standard Uno I2C)"),
    (19, 18, "A5=SDA, A4=SCL"),
]
# If any pair of pins is HIGH, add them as candidate pairs
for sda in high_pins:
    for scl in high_pins:
        if sda != scl and (sda, scl) not in [(18,19), (19,18)]:
            candidate_pairs.append((sda, scl, f"{pin_names[sda]}=SDA, {pin_names[scl]}=SCL"))

print("\\n2. Testing I2C Address 0x48 (ADS1015/ADS1115) on candidate pin pairs:")
print("-" * 65)
found_ack = False
for sda, scl, desc in candidate_pairs:
    for test_addr in [0x48, 0x49, 0x4A, 0x4B]:
        ack = bb_i2c_probe(sda, scl, test_addr)
        if ack:
            print(f"  >>> SUCCESS: ACK received on {desc} at Address 0x{test_addr:02X}!")
            found_ack = True
            break
    if not ack:
        print(f"  Tested {desc}: No ACK on 0x48..0x4B")

devmode.stop()
print("\\n" + "=" * 65)
'''

def main():
    client = PYNQAgentClient()
    print("[Host] Running pin logic probe...")
    client.write_file("/home/xilinx/probe_i2c_pins_remote.py", content=REMOTE_PROBE_CODE)
    res = client.run_python("/home/xilinx", "probe_i2c_pins_remote.py", timeout=90)
    print("\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

if __name__ == "__main__":
    main()
