import os

content = """---
name: linkedin-thought-leadership-skill
description: Generates high-impact, viral LinkedIn thought leadership posts, technical breakdowns, system architecture diagrams, and cost-efficiency reports from workspace achievements.
---

# LinkedIn Thought Leadership & Public Authority Skill (`39-linkedin-thought-leadership-skill`)

Empowers Rahul to publish world-class technical posts showcasing cutting-edge engineering capabilities, autonomous agent fleet architectures, FPGA/DSP physical experiments, local GPU delegation, and system benchmark breakthroughs.

---

## Strict Formatting & Length Directives (MANDATORY)

1. **Length: Strict 50% - 70% of Maximum Post Size**
   - LinkedIn allows up to 3,000 characters.
   - Every post MUST be strictly **50% to 70% of max size** (~1,500 to 2,100 characters, ~220 to 320 words).
   - Cut all fluff, filler, and repetitive prose. Every line must carry technical density.

2. **NO Markdown Heading Tags (Zero `#`, `##`, `###`)**
   - LinkedIn does NOT render markdown heading syntax. Pasting `### Heading` or `## Section` into LinkedIn looks messy and unrendered.
   - **Never** include `#`, `##`, or `###` headings in the post text.
   - For section headers, use **Uppercase Line Headers** (e.g., `THE HARDWARE ARCHITECTURE:`, `3 CRITICAL LESSONS:`, `WHAT COMES NEXT:`) or emoji prefixes with clean bolding.

3. **Clean, Ready-to-Paste Typography**
   - Use clean spacing and standard bullet points (`•` or `-`).
   - Use standard Unicode arrows (`→`) for dataflow pipelines.
   - Keep ASCII diagrams compact (under 12 lines) so they do not break on mobile screens.

4. **Zero Outbound Links in Post Body**
   - External links trigger LinkedIn reach suppression.
   - Always state: *"Source code and architecture spec in the first comment."*

---

## Core Content Framework
1. **The Scroll-Stopping Technical Hook**: Challenging conventional dogma in the first 2 lines (before the 'see more' fold).
2. **Compact System Architecture**: Clean, high-density flow diagram showing end-to-end hardware/software dataflow.
3. **Hard Proof & Benchmarks**: Real empirical measurements (sample rates, latency in microseconds, voltage in mV, power in Watts).
4. **The Counter-Intuitive Lesson / Gotcha**: A real engineering trap and the architectural solution.
5. **Community Debate CTA**: A targeted question that invites senior engineers to discuss design trade-offs in the comments.
"""

target_path = r"H:\life\07-projects\02-ai skills\39-linkedin-thought-leadership-skill\SKILL.md"
with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully updated: {target_path}")
