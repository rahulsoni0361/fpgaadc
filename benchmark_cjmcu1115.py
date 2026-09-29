"""
benchmark_cjmcu1115.py - Phase 1 & 2 PS Acquisition Benchmark for CJMCU-1115 (ADS1115)
Target: PYNQ Arduino Header I2C @ Address 0x48, Channel A0 (10 cm jumper wire)
Implements specs.md Phase 1 (Throughput Baseline) & Phase 2 (Statistical Characterization).
"""

import sys
import os
import json
import time
sys.path.insert(0, r"H:\life\07-projects\02-ai skills\01-embedded-hardware\pynq-skills\scripts")
from pynq_deploy import PYNQAgentClient

REMOTE_SCRIPT = '''
import time
import json
import numpy as np
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard
from cjmcu_ads1115 import ADS1115

def run_benchmark(num_samples=1000):
    print("=" * 65)
    print(" CJMCU-1115 (ADS1115 16-BIT) PS BENCHMARK - PHASE 1 & 2")
    print("=" * 65)
    print(f"I2C Address: 0x48 (ADDR -> GND)")
    print(f"Target Input: Channel A0 (Single-Ended AIN0 vs GND)")
    print(f"Target Sample Count: N = {num_samples}")

    print("Initializing BaseOverlay ('base.bit')...")
    base = BaseOverlay('base.bit')

    print("Initializing Arduino DevMode & I2C Controller...")
    devmode = ard.Arduino_DevMode(base.ARDUINO, ard.ARDUINO_SWCFG_DIOALL)
    devmode.start()

    ads = ADS1115(devmode, address=0x48)
    
    # Configure for AIN0 vs GND, +/- 2.048V, Continuous Mode, 860 SPS (max rate)
    print("Configuring ADS1115: Channel A0, +/- 2.048V, Continuous, 860 SPS...")
    ads.write_config(
        mux=ADS1115.MUX_SINGLE_0,
        pga=ADS1115.PGA_2_048V,
        mode=ADS1115.MODE_CONTINUOUS,
        dr=ADS1115.DR_860SPS
    )
    time.sleep(0.02)

    # Warm-up read
    warm_raw = ads.read_raw()
    warm_v = ads.read_voltage()
    print(f"Warm-up Sample -> Raw: {warm_raw} (0x{warm_raw & 0xFFFF:04X}) | Voltage: {warm_v:+.4f} V\\n")

    print(f"Starting Acquisition of N = {num_samples} samples...")
    raw_samples = []
    voltages = []
    timestamps = []

    t_start = time.perf_counter()
    for i in range(num_samples):
        t_now = time.perf_counter()
        raw = ads.read_raw()
        if raw is not None:
            raw_samples.append(raw)
            voltages.append(raw * ads.lsb_volts)
            timestamps.append(t_now - t_start)
    t_end = time.perf_counter()

    elapsed = t_end - t_start
    actual_n = len(raw_samples)
    f_sample = actual_n / elapsed
    t_sample_ms = (elapsed / actual_n) * 1000.0

    raw_arr = np.array(raw_samples, dtype=np.int32)
    volt_arr = np.array(voltages, dtype=np.float64)

    # Timing intervals
    dt_arr = np.diff(timestamps)
    dt_min_ms = float(np.min(dt_arr) * 1000.0) if len(dt_arr) > 0 else 0
    dt_max_ms = float(np.max(dt_arr) * 1000.0) if len(dt_arr) > 0 else 0
    dt_std_ms = float(np.std(dt_arr) * 1000.0) if len(dt_arr) > 0 else 0

    # Statistical characterization
    raw_min = int(np.min(raw_arr))
    raw_max = int(np.max(raw_arr))
    v_pp_code = raw_max - raw_min
    mu_code = float(np.mean(raw_arr))
    sigma_code = float(np.std(raw_arr))
    rms_code = float(np.sqrt(np.mean(raw_arr.astype(float)**2)))

    v_min = float(np.min(volt_arr))
    v_max = float(np.max(volt_arr))
    v_pp = v_max - v_min
    mu_v = float(np.mean(volt_arr))
    sigma_v = float(np.std(volt_arr))
    rms_v = float(np.sqrt(np.mean(volt_arr**2)))

    print("=" * 65)
    print(" PHASE 1 ACQUISITION BENCHMARK RESULTS")
    print("=" * 65)
    print(f"Total Valid Samples:        {actual_n} / {num_samples}")
    print(f"Elapsed Time:               {elapsed:.4f} s")
    print(f"Effective Sampling Rate:    {f_sample:.2f} samples/sec (Hz)")
    print(f"Average Sample Interval:    {t_sample_ms:.3f} ms")
    print(f"Interval Min / Max:         {dt_min_ms:.3f} ms / {dt_max_ms:.3f} ms")
    print(f"Interval Jitter (Std Dev):  {dt_std_ms:.3f} ms")

    print("\\n" + "=" * 65)
    print(" PHASE 2 STATISTICAL CHARACTERIZATION (16-Bit ADS1115)")
    print("=" * 65)
    print(f"Code Range:                 [{raw_min} .. {raw_max}] (Vpp: {v_pp_code} codes)")
    print(f"Mean Code:                  {mu_code:.2f} codes")
    print(f"Code Std Dev:               {sigma_code:.2f} codes")
    print(f"Code RMS:                   {rms_code:.2f} codes")
    print(f"Voltage Range:              [{v_min:+.4f} V .. {v_max:+.4f} V] (Vpp: {v_pp:.4f} V)")
    print(f"DC Level (Mean Voltage):    {mu_v:+.4f} V")
    print(f"Voltage Std Dev:            {sigma_v:.4f} V")
    print(f"Voltage RMS:                {rms_v:.4f} V")

    # Histogram
    hist_counts, bin_edges = np.histogram(raw_arr, bins=min(10, max(1, v_pp_code + 1)))
    print("\\nHistogram of 16-bit Raw Codes:")
    for count, b_left, b_right in zip(hist_counts, bin_edges[:-1], bin_edges[1:]):
        bar = "#" * int(40 * count / max(hist_counts))
        print(f"  [{int(b_left):6d} .. {int(b_right):6d}]: {count:4d} {bar}")

    # First 10 samples preview
    print("\\nFirst 10 Live Samples:")
    for k in range(min(10, actual_n)):
        print(f"  [{k+1:2d}] t = {timestamps[k]*1000:7.2f} ms | Code = {raw_arr[k]:6d} | Volt = {volt_arr[k]:+.4f} V")

    devmode.stop()

    # Export results JSON
    results = {
        "device": "CJMCU-1115 (ADS1115 16-Bit ADC)",
        "i2c_address": "0x48",
        "channel": "A0 (AIN0 vs GND)",
        "num_samples": actual_n,
        "elapsed_time_s": elapsed,
        "sampling_rate_hz": f_sample,
        "sample_interval_ms": t_sample_ms,
        "jitter_std_ms": dt_std_ms,
        "min_code": raw_min,
        "max_code": raw_max,
        "vpp_code": v_pp_code,
        "mean_code": mu_code,
        "std_code": sigma_code,
        "rms_code": rms_code,
        "min_voltage_v": v_min,
        "max_voltage_v": v_max,
        "vpp_v": v_pp,
        "mean_voltage_v": mu_v,
        "std_voltage_v": sigma_v,
        "rms_voltage_v": rms_v,
        "samples_code": raw_samples[:300],
        "timestamps_s": timestamps[:300]
    }
    with open('/home/xilinx/cjmcu1115_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\\nResults saved to /home/xilinx/cjmcu1115_results.json")

if __name__ == '__main__':
    run_benchmark(1000)
'''

def main():
    client = PYNQAgentClient()
    print("[Host] Connecting to PYNQ board @ 192.168.1.155...")
    ping = client.ping()
    print(f"[Host] PYNQ Board Online! FPGA State: {ping.get('fpga_state')}")

    # Upload driver and benchmark script
    local_dir = os.path.dirname(__file__)
    with open(os.path.join(local_dir, "cjmcu_ads1115.py"), "r", encoding="utf-8") as f:
        driver_code = f.read()
    client.write_file("/home/xilinx/cjmcu_ads1115.py", content=driver_code)
    client.write_file("/home/xilinx/benchmark_cjmcu1115_run.py", content=REMOTE_SCRIPT)
    print("[Host] Uploaded driver and benchmark script to board.")

    print("[Host] Executing Phase 1 & 2 Benchmark (N = 1000)...")
    res = client.run_python("/home/xilinx", "benchmark_cjmcu1115_run.py", timeout=120)

    # Print output avoiding cp1252 unicode errors
    stdout_text = res.get("stdout", "")
    for line in stdout_text.splitlines():
        try:
            print(line)
        except Exception:
            print(line.encode("ascii", "replace").decode("ascii"))

    if res.get("stderr"):
        print("STDERR:\n" + res.get("stderr", ""))

    # Fetch results JSON back to host
    print("\n[Host] Fetching results JSON to local directory...")
    exec_res = client.exec("cat /home/xilinx/cjmcu1115_results.json")
    if exec_res.get("stdout"):
        local_json_path = os.path.join(local_dir, "cjmcu1115_results.json")
        with open(local_json_path, "w", encoding="utf-8") as f:
            f.write(exec_res["stdout"])
        print(f"[Host] Benchmark results successfully saved to: {local_json_path}")

if __name__ == "__main__":
    main()
