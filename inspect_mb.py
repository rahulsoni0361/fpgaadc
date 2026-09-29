import sys
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

client = PYNQAgentClient()
code = """
import inspect
from pynq.overlays.base import BaseOverlay
import pynq.lib.pynqmicroblaze as pmb

print("pmb symbols:", dir(pmb))

base = BaseOverlay('base.bit')
mb = base.iop_arduino
print("iop_arduino type:", type(mb))
print("iop_arduino dir:", [x for x in dir(mb) if not x.startswith('_')])
"""
client.write_file("/home/xilinx/test_mb.py", content=code)
res = client.run_python("/home/xilinx", "test_mb.py", timeout=60)
print(res.get("stdout"))
print(res.get("stderr"))
