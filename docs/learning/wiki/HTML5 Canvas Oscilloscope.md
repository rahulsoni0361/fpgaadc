[[live-dsp-browser-pipeline]]

*Context: Extracted from the live-dsp-browser-pipeline document regarding the FPGA ADC to browser DSP dashboard.*

# HTML5 Canvas Oscilloscope

The **HTML5 Canvas Oscilloscope** renders live, high-frequency voltage traces inside the web browser with zero external JavaScript dependencies.

## Key Design & Implementation Decisions

1. **HiDPI Retina Scaling**:
   Canvases are sized to match the physical device pixel ratio to prevent pixelation:
   ```javascript
   canvas.width = canvas.clientWidth * window.devicePixelRatio;
   canvas.height = canvas.clientHeight * window.devicePixelRatio;
   ```

2. **Phosphor Glow Emulation**:
   To mimic the aesthetic of a hardware analog oscilloscope cathode ray tube (CRT):
   ```javascript
   ctx.strokeStyle = '#00f2fe';
   ctx.shadowColor = '#00f2fe';
   ctx.shadowBlur = 8;
   ctx.lineWidth = 2.2 * window.devicePixelRatio;
   ```

3. **Dynamic Auto-Scaling**:
   The vertical scale calculates min and max dynamically per frame with a safety margin, ensuring low-amplitude (2.7 mV) microvolt signals remain vividly visible without clipping.

[[live-dsp-browser-pipeline]]
