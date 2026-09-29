"""
test_detect_adc.py - Test ADC on Arduino header via pynq.lib.arduino
"""

import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

def main():
    client = PYNQAgentClient()

    remote_code = '''
import time
import numpy as np
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard

print("==================================================")
print(" 1. Initializing PYNQ Base Overlay")
print("==================================================")
base = BaseOverlay('base.bit')
print("Base overlay loaded successfully.")

print("\\n==================================================")
print(" 2. Probing Arduino Header Analog ADC (Pin A0)")
print("==================================================")
try:
    print("Initializing ard.Arduino_Analog(base.ARDUINO, [0])...")
    analog_in = ard.Arduino_Analog(base.ARDUINO, [0])
    print("SUCCESS: Arduino_Analog initialized on pin A0!")
    
    # Read 10 samples
    print("\\nReading live samples from pin A0 (floating / jumper wire):")
    for i in range(10):
        raw = analog_in.read_raw()
        voltage = analog_in.read('voltage')
        raw_val = int(np.atleast_1d(raw)[0])
        volt_val = float(np.atleast_1d(voltage)[0])
        print(f"  [Sample {i+1:2d}] Raw: {raw_val:4d} (0x{raw_val:03X}) | Voltage: {volt_val:.4f} V")
        time.sleep(0.2)
        
    print("\\nResetting analog peripheral...")
    analog_in.reset()
except Exception as e:
    import traceback
    print(f"Arduino_Analog error: {e}")
    traceback.print_exc()

print("\\n==================================================")
print(" 3. Probing External Grove I2C ADC (if connected)")
print("==================================================")
try:
    print("Initializing ard.Grove_ADC(base.ARDUINO, ard.ARDUINO_GROVE_I2C)...")
    grove_adc = ard.Grove_ADC(base.ARDUINO, ard.ARDUINO_GROVE_I2C)
    print("Grove_ADC instance created! Attempting live read...")
    raw_val = grove_adc.read_raw()
    volt_val = grove_adc.read()
    print(f"SUCCESS: Grove I2C ADC detected! Raw: {raw_val}, Voltage: {volt_val:.4f} V")
    grove_adc.reset()
except Exception as e:
    print(f"Grove_ADC notice: {e}")

print("\\n==================================================")
print(" Detection & Sampling Complete")
print("==================================================")
'''
    client.write_file("/home/xilinx/detect_adc_remote.py", content=remote_code)
    print("Running detection script on PYNQ board...")
    res = client.run_python("/home/xilinx", "detect_adc_remote.py", timeout=90)
    print("\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

if __name__ == "__main__":
    main()
