"""
render_mermaid_to_png.py - Render Mermaid Diagrams to High-Resolution PNGs
Uses local offline mermaid.min.js from mermaid-skill and Headless Chrome.
"""

import os
import sys
import subprocess
import time

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

MERMAID_JS = r"H:\life\07-projects\02-ai skills\03-coding-infrastructure\Agent-framework\Project-management-skills-and-agents\mermaid-skill\resources\mermaid.min.js"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      background-color: #0b0f19;
      color: #f0f4fc;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 40px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      box-sizing: border-box;
    }
    #container {
      background: #121826;
      border: 1px solid #2a3449;
      border-radius: 16px;
      padding: 32px 40px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
      display: inline-block;
    }
    .mermaid {
      display: flex;
      justify-content: center;
    }
  </style>
  <script src="__MERMAID_JS_PATH__"></script>
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#121826',
        primaryColor: '#1e293b',
        primaryTextColor: '#f8fafc',
        primaryBorderColor: '#00f2fe',
        lineColor: '#38bdf8',
        secondaryColor: '#0f172a',
        tertiaryColor: '#1e293b'
      }
    });
  </script>
</head>
<body>
  <div id="container">
    <div class="mermaid">
__MERMAID_CODE__
    </div>
  </div>
</body>
</html>
"""

def render_mermaid(mermaid_code, output_png, width=1600, height=1000):
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    temp_html = output_png.replace(".png", "_temp.html")
    
    js_uri = "file:///" + MERMAID_JS.replace("\\", "/")
    html_content = HTML_TEMPLATE.replace("__MERMAID_JS_PATH__", js_uri).replace("__MERMAID_CODE__", mermaid_code.strip())
    
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    html_uri = "file:///" + os.path.abspath(temp_html).replace("\\", "/")
    
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        f"--screenshot={os.path.abspath(output_png)}",
        f"--window-size={width},{height}",
        "--virtual-time-budget=4000",
        html_uri
    ]
    
    print(f"Rendering {output_png}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    
    if os.path.exists(temp_html):
        os.remove(temp_html)
        
    if os.path.exists(output_png) and os.path.getsize(output_png) > 1000:
        print(f"[SUCCESS] Rendered PNG: {output_png} ({os.path.getsize(output_png)} bytes)")
        return True
    else:
        print(f"[ERROR] Failed to render PNG. Output: {res.stderr}")
        return False

if __name__ == "__main__":
    test_code = """
    graph LR
        A[Physical ADC] --> B[FPGA Ring Buffer]
        B --> C[DSP Engine]
        C --> D[RTX 3090 GPU]
    """
    test_out = r"h:\07-projects\03-inhouse-projects\fpgaadc\test_diagram.png"
    render_mermaid(test_code, test_out)
