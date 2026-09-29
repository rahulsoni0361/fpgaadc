"""
test_grove_i2c_adc.py - Check specifically for an external Grove I2C ADC module
"""

import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

def main():
    client = PYNQAgentClient()

    remote_code = '''
import time
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard

print("Loading fresh BaseOverlay...")
base = BaseOverlay('base.bit')

print("Probing Grove I2C ADC (ADC121C021)...")
try:
    grove_adc = ard.Grove_ADC(base.ARDUINO, ard.ARDUINO_GROVE_I2C)
    print("Grove_ADC driver loaded successfully.")
    
    print("Reading 5 samples from Grove I2C ADC:")
    for i in range(5):
        raw = grove_adc.read_raw()
        voltage = grove_adc.read()
        print(f"  [I2C Sample {i+1}] Raw: {raw} | Voltage: {voltage:.4f} V")
        time.sleep(0.3)
    print("SUCCESS: External Grove I2C ADC is connected and responding!")
except Exception as e:
    print(f"Grove I2C ADC not responding or not present: {e}")
'''
    client.write_file("/home/xilinx/test_grove_remote.py", content=remote_code)
    print("Running Grove I2C ADC probe on PYNQ board...")
    res = client.run_python("/home/xilinx", "test_grove_remote.py", timeout=90)
    print("\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

if __name__ == "__main__":
    main()
