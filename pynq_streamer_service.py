"""
pynq_streamer_service.py - Real-Time ADC Streaming Daemon for PYNQ-Z2
Runs on PYNQ board, keeps BaseOverlay & I2C controller loaded in memory,
and samples the ADS1115 continuously into a high-speed ring buffer.
Serves samples over lightweight HTTP on port 5050.
"""

import time
import json
import threading
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import numpy as np

# PYNQ hardware imports
from pynq.overlays.base import BaseOverlay
import pynq.lib.arduino as ard
from cjmcu_ads1115 import ADS1115

PORT = 5050
BUFFER_SIZE = 4096

class ADCStreamer:
    def __init__(self):
        print("[Streamer] Loading BaseOverlay('base.bit')...")
        self.base = BaseOverlay('base.bit')
        print("[Streamer] Initializing Arduino DevMode...")
        self.devmode = ard.Arduino_DevMode(self.base.ARDUINO, ard.ARDUINO_SWCFG_DIOALL)
        self.devmode.start()
        
        print("[Streamer] Initializing ADS1115 at 0x48...")
        self.ads = ADS1115(self.devmode, address=0x48)
        self.ads.write_config(
            mux=ADS1115.MUX_SINGLE_0,
            pga=ADS1115.PGA_2_048V,
            mode=ADS1115.MODE_CONTINUOUS,
            dr=ADS1115.DR_860SPS
        )
        
        self.buffer = deque(maxlen=BUFFER_SIZE)
        self.time_buffer = deque(maxlen=BUFFER_SIZE)
        self.lock = threading.Lock()
        self.running = False
        self.sample_count = 0
        self.effective_fs = 117.0
        self.t_start = 0.0

    def start_acquisition(self):
        self.running = True
        self.t_start = time.perf_counter()
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        print("[Streamer] Continuous ADC acquisition thread started.")

    def _worker(self):
        last_t = time.perf_counter()
        while self.running:
            v = self.ads.read_voltage()
            now = time.perf_counter()
            if v is not None:
                with self.lock:
                    self.buffer.append(float(v))
                    self.time_buffer.append(float(now - self.t_start))
                    self.sample_count += 1
                    
                    if self.sample_count % 100 == 0 and len(self.time_buffer) >= 2:
                        dt = self.time_buffer[-1] - self.time_buffer[0]
                        if dt > 0:
                            self.effective_fs = (len(self.time_buffer) - 1) / dt

    def get_latest(self, n=256):
        with self.lock:
            buf_len = len(self.buffer)
            n_fetch = min(n, buf_len)
            if n_fetch == 0:
                return [], [], 0.0, 0
            
            # Slice the latest n_fetch items
            samples = list(self.buffer)[-n_fetch:]
            times = list(self.time_buffer)[-n_fetch:]
            fs = self.effective_fs
            total = self.sample_count
        return samples, times, fs, total

streamer = None

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/data":
            qs = parse_qs(parsed.query)
            n = int(qs.get("n", [256])[0])
            samples, times, fs, total = streamer.get_latest(n)
            
            payload = {
                "source": "ADS1115_A0",
                "sample_count": len(samples),
                "total_acquired": total,
                "fs": round(fs, 2),
                "samples": samples,
                "times": times
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            
        elif parsed.path == "/stats":
            samples, times, fs, total = streamer.get_latest(256)
            if samples:
                arr = np.array(samples)
                stats = {
                    "fs": round(fs, 2),
                    "total_samples": total,
                    "mean_v": round(float(np.mean(arr)), 5),
                    "rms_v": round(float(np.sqrt(np.mean(arr**2))), 5),
                    "vpp_mv": round(float(np.ptp(arr) * 1000.0), 3),
                    "min_v": round(float(np.min(arr)), 5),
                    "max_v": round(float(np.max(arr)), 5)
                }
            else:
                stats = {"status": "buffering", "total_samples": total}
                
            body = json.dumps(stats).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            
        elif parsed.path == "/ping":
            body = b'{"status": "ok", "service": "pynq_adc_streamer"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress HTTP access logging for maximum speed

if __name__ == "__main__":
    streamer = ADCStreamer()
    streamer.start_acquisition()
    print(f"[Streamer] Server listening on http://0.0.0.0:{PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), StreamHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[Streamer] Shutting down...")
        streamer.running = False
        server.server_close()
