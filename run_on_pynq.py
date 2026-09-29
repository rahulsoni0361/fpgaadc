"""
run_on_pynq.py - Universal helper to run code or commands on PYNQ board cleanly.
"""

import sys
import os
import argparse
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

client = PYNQAgentClient()

def run_bash(cmd, sudo=False):
    res = client.exec(cmd, sudo=sudo, timeout=120)
    print("STDOUT:\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))
    return res

def run_py_code(code_str):
    client.write_file("/home/xilinx/tmp_run.py", content=code_str)
    res = client.run_python("/home/xilinx", "tmp_run.py", timeout=120)
    print("STDOUT:\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))
    return res

def run_py_file(local_path):
    with open(local_path, "r", encoding="utf-8") as f:
        code_str = f.read()
    remote_name = os.path.basename(local_path)
    client.write_file(f"/home/xilinx/{remote_name}", content=code_str)
    res = client.run_python("/home/xilinx", remote_name, timeout=120)
    print("STDOUT:\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))
    return res

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--code", type=str, help="Python code to run")
    parser.add_argument("-f", "--file", type=str, help="Local python file to upload and run")
    args, unknown = parser.parse_known_args()

    if args.code:
        run_py_code(args.code)
    elif args.file:
        run_py_file(args.file)
    elif unknown:
        run_bash(" ".join(unknown))
    else:
        parser.print_help()
