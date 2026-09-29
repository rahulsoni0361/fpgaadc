"""
ps_adc_benchmark.py - Phase 1 & 2: PS ADC Acquisition & Characterization
Target: PYNQ-Z2 Arduino Header Pin A0 via pynq.lib.arduino.Arduino_Analog
Implements specs.md Phase 1 (Throughput Baseline) & Phase 2 (Statistical Characterization).
"""

import sys
import os
import json
import time
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

# Remote benchmark script executed on PYNQ board under pynq-venv
REMOTE_BENCHMARK_CODE = '''
import time
import json
import math
import numpy as np
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard

def run_benchmark(num_samples=1000):
    print("=" * 65)
    print(" FPGA ADC -> DSP STRESS PROJECT: PHASE 1 & 2 PS BASELINE")
    print("=" * 65)
    print(f"Target: Arduino Header Pin A0 (Analog 0)")
    print(f"Sample Count Requested: N = {num_samples}")
    print("Initializing BaseOverlay ('base.bit')...")
    base = BaseOverlay('base.bit')
    
    print("Initializing pynq.lib.arduino.Arduino_Analog(base.ARDUINO, [0])...")
    adc = ard.Arduino_Analog(base.ARDUINO, [0])
    print("ADC Peripheral ready!\\n")

    # -------------------------------------------------------------
    # 1. Warm-up read
    # -------------------------------------------------------------
    warmup_raw = int(np.atleast_1d(adc.read_raw())[0])
    warmup_v = float(np.atleast_1d(adc.read('voltage'))[0])
    print(f"Warm-up Verification Sample -> Raw: {warmup_raw} (0x{warmup_raw:03X}), Voltage: {warmup_v:.4f} V\\n")

    # -------------------------------------------------------------
    # 2. Benchmark: Point-by-point Polling (Python PS Loop)
    # -------------------------------------------------------------
    print(f"--- Running Python PS Polling Benchmark (N = {num_samples}) ---")
    raw_samples = []
    voltages = []
    timestamps = []

    t_start = time.perf_counter()
    for i in range(num_samples):
        t_sample = time.perf_counter()
        raw = int(np.atleast_1d(adc.read_raw())[0])
        raw_samples.append(raw)
        timestamps.append(t_sample - t_start)
    t_end = time.perf_counter()

    elapsed_time = t_end - t_start
    f_sample = num_samples / elapsed_time
    t_sample_avg_ms = (elapsed_time / num_samples) * 1000.0

    raw_arr = np.array(raw_samples, dtype=np.int32)
    # V_Conv for XADC Arduino is 3.3V / 4096 (12-bit)
    volt_arr = raw_arr * (3.3 / 4096.0)

    # Calculate intervals
    dt_arr = np.diff(timestamps)
    dt_avg_ms = np.mean(dt_arr) * 1000.0 if len(dt_arr) > 0 else 0
    dt_min_ms = np.min(dt_arr) * 1000.0 if len(dt_arr) > 0 else 0
    dt_max_ms = np.max(dt_arr) * 1000.0 if len(dt_arr) > 0 else 0
    dt_std_ms = np.std(dt_arr) * 1000.0 if len(dt_arr) > 0 else 0

    # -------------------------------------------------------------
    # 3. Statistical Characterization (Phase 2)
    # -------------------------------------------------------------
    mu = float(np.mean(raw_arr))
    sigma = float(np.std(raw_arr))
    raw_min = int(np.min(raw_arr))
    raw_max = int(np.max(raw_arr))
    v_pp_code = raw_max - raw_min
    rms = float(np.sqrt(np.mean(raw_arr.astype(float)**2)))
    
    mu_v = float(np.mean(volt_arr))
    sigma_v = float(np.std(volt_arr))
    v_min = float(np.min(volt_arr))
    v_max = float(np.max(volt_arr))
    v_pp = v_max - v_min
    rms_v = float(np.sqrt(np.mean(volt_arr**2)))

    # Compute histogram (10 bins across the observed range)
    hist_counts, bin_edges = np.histogram(raw_arr, bins=min(10, max(1, v_pp_code + 1)))

    print("=" * 65)
    print(" ACQUISITION METRICS (Phase 1)")
    print("=" * 65)
    print(f"Total Samples (N):          {num_samples}")
    print(f"Elapsed Time:               {elapsed_time:.4f} s")
    print(f"Effective Sampling Rate:    {f_sample:.2f} samples/sec (Hz)")
    print(f"Average Sample Interval:    {t_sample_avg_ms:.3f} ms")
    print(f"Sample Interval Min / Max:  {dt_min_ms:.3f} ms / {dt_max_ms:.3f} ms")
    print(f"Interval Jitter (Std Dev):  {dt_std_ms:.3f} ms")

    print("\\n" + "=" * 65)
    print(" STATISTICAL CHARACTERIZATION (Phase 2 - Raw 12-bit ADC & Voltage)")
    print("=" * 65)
    print(f"ADC Code Range:             [{raw_min} .. {raw_max}] (Peak-to-Peak: {v_pp_code} codes)")
    print(f"DC Level (Mean Code \\u03bc):      {mu:.2f} codes ({mu_v:.4f} V)")
    print(f"Standard Deviation (\\u03c3):      {sigma:.2f} codes ({sigma_v:.4f} V)")
    print(f"RMS:                        {rms:.2f} codes ({rms_v:.4f} V)")
    print(f"Voltage Range:              [{v_min:.4f} V .. {v_max:.4f} V] (Vpp: {v_pp:.4f} V)")

    print("\\nHistogram of Raw ADC Codes:")
    for count, b_left, b_right in zip(hist_counts, bin_edges[:-1], bin_edges[1:]):
        bar = "#" * int(40 * count / max(hist_counts))
        print(f"  [{int(b_left):4d} .. {int(b_right):4d}]: {count:4d} {bar}")

    # First 10 samples preview
    print("\\nFirst 10 Captured Samples:")
    for k in range(min(10, num_samples)):
        print(f"  [{k+1:2d}] t = {timestamps[k]*1000:7.2f} ms | Raw = {raw_arr[k]:4d} | Volt = {volt_arr[k]:.4f} V")

    # Clean up
    adc.reset()

    # Pack results for JSON export
    results = {
        "num_samples": num_samples,
        "elapsed_time_s": elapsed_time,
        "sampling_rate_hz": f_sample,
        "sample_interval_ms": t_sample_avg_ms,
        "jitter_std_ms": dt_std_ms,
        "min_code": raw_min,
        "max_code": raw_max,
        "pp_code": v_pp_code,
        "mean_code": mu,
        "std_code": sigma,
        "rms_code": rms,
        "mean_voltage_v": mu_v,
        "std_voltage_v": sigma_v,
        "min_voltage_v": v_min,
        "max_voltage_v": v_max,
        "vpp_v": v_pp,
        "samples_raw": raw_samples[:200],  # first 200 samples
        "timestamps_s": timestamps[:200]
    }
    with open('/home/xilinx/ps_adc_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\\nResults written to /home/xilinx/ps_adc_results.json")

if __name__ == '__main__':
    run_benchmark(1000)
'''

def main():
    client = PYNQAgentClient()
    print("[Host] Connecting to PYNQ board @ 192.168.1.155...")
    ping = client.ping()
    print(f"[Host] Board Online! FPGA State: {ping.get('fpga_state')}")

    # Write remote script
    remote_script_path = "/home/xilinx/ps_adc_benchmark_run.py"
    client.write_file(remote_script_path, content=REMOTE_BENCHMARK_CODE)
    print(f"[Host] Uploaded benchmark script to {remote_script_path}")

    # Execute
    print("[Host] Running Phase 1 & 2 Benchmark (N = 1000)...")
    res = client.run_python("/home/xilinx", "ps_adc_benchmark_run.py", timeout=120)

    print("\n" + res.get("stdout", ""))
    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

    # Download results JSON
    print("[Host] Fetching benchmark results JSON...")
    exec_res = client.exec("cat /home/xilinx/ps_adc_results.json")
    if exec_res.get("stdout"):
        local_json_path = os.path.join(os.path.dirname(__file__), "ps_adc_results.json")
        with open(local_json_path, "w") as f:
            f.write(exec_res["stdout"])
        print(f"[Host] Saved benchmark results locally to: {local_json_path}")

if __name__ == "__main__":
    main()
