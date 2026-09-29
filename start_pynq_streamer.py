import sys
import time
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

client = PYNQAgentClient()
print("Stopping previous streamer if running...")
client.exec("systemctl stop pynq-streamer", sudo=True)
client.exec("systemctl reset-failed pynq-streamer", sudo=True)

print("Starting pynq-streamer under systemd with login environment...")
cmd = "systemd-run --unit=pynq-streamer bash -l -c 'cd /home/xilinx && /usr/local/share/pynq-venv/bin/python3 -u /home/xilinx/pynq_streamer_service.py'"
res = client.exec(cmd, sudo=True)
print("Launch response:", res)

print("Waiting for FPGA overlay and ADC initialization...")
time.sleep(6)

log = client.exec("journalctl -u pynq-streamer --no-pager -n 25", sudo=True)
print("=== PYNQ STREAMER LOG ===")
print(log.get("stdout", ""))

# Test endpoint
print("Testing /stats endpoint...")
test = client.exec("curl -s http://127.0.0.1:5050/stats")
print("Stats response:", test.get("stdout", ""))
