import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

client = PYNQAgentClient()
code = """
from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze import MicroblazeProgram

base = BaseOverlay('base.bit')
c_code = '''
#include <i2c.h>

int test_add(int a, int b) {
    return a + b;
}
'''
print("Compiling test MicroblazeProgram...")
mb_prog = MicroblazeProgram(base.iop_arduino, c_code)
result = mb_prog.test_add(10, 25)
print(f"Result from MicroBlaze: 10 + 25 = {result}")
"""
client.write_file("/home/xilinx/test_mb_prog.py", content=code)
res = client.run_python("/home/xilinx", "test_mb_prog.py", timeout=60)
print(res.get("stdout"))
print(res.get("stderr"))
