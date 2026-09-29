"""
probe_arduino.py - Inspect Arduino subsystem and I2C interfaces on PYNQ-Z2
"""

import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

def main():
    client = PYNQAgentClient()
    print("Testing connection to PYNQ board...")
    ping = client.ping()
    print("Ping response:", ping)

    # Remote probe script to run under PYNQ venv
    remote_script = """
import pynq
from pynq.overlays.base import BaseOverlay

print("PYNQ Version:", pynq.__version__)
base = BaseOverlay('base.bit')
print("BaseOverlay loaded successfully!")
print("BaseOverlay attributes:")
for attr in dir(base):
    if not attr.startswith('_'):
        print(f"  {attr}")

print("\\nIP Dict keys:")
for k in base.ip_dict.keys():
    print(f"  {k}")

print("\\nChecking Arduino IP:")
if hasattr(base, 'iop_arduino'):
    print("Found base.iop_arduino:", type(base.iop_arduino))
if hasattr(base, 'ARDUINO'):
    print("Found base.ARDUINO:", type(base.ARDUINO), base.ARDUINO)

import pynq.lib.arduino as ard
print("\\nArduino lib contents:")
print([x for x in dir(ard) if not x.startswith('_')])
"""
    client.write_file("/home/xilinx/probe_arduino_remote.py", content=remote_script)
    print("\nRunning probe script on board...")
    res = client.run_python("/home/xilinx", "probe_arduino_remote.py", timeout=60)
    print("Exit code:", res.get("exit_code"))
    print("STDOUT:\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

if __name__ == "__main__":
    main()
