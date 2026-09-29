# build_pl_dsp.tcl
# Vivado 2026.1 Synthesis & Resource Utilization Script for PYNQ-Z2 PL DSP Accelerator
# Target: xc7z020clg400-1

set part "xc7a100tcsg324-1"
set project_name "pynq_pl_dsp_synth"
set output_dir [file normalize "./vivado_output"]

file mkdir $output_dir

puts "=========================================================="
puts " Vivado 2026.1 PL DSP Accelerator Synthesis"
puts " Target Architecture: 7-Series DSP48E1 Fabric ($part)"
puts "=========================================================="

# Create In-Memory Project
create_project -in_memory -part $part

# Add Verilog Source Files
read_verilog "./src/verilog/pl_fir_filter_16.v"
read_verilog "./src/verilog/pl_dsp_accelerator_top.v"

# Set Top Module
set_property top pl_dsp_accelerator_top [current_fileset]

# Synthesize Design
puts "\n[*] Running Vivado Synthesis..."
synth_design -top pl_dsp_accelerator_top -part $part -mode out_of_context

# Generate Utilization Reports
puts "\n[*] Generating Resource Utilization & Timing Reports..."
report_utilization -file [file join $output_dir "utilization_report.txt"]
report_timing_summary -file [file join $output_dir "timing_report.txt"]

# Extract Key Metrics to Console
puts "\n=========================================================="
puts " SYNTHESIS COMPLETED SUCCESSFULLY"
puts "=========================================================="
set dsp_count [get_property DSP [get_cells -hierarchical -filter {PRIMITIVE_TYPE =~ MULT.dsp.*}]]
puts "Report written to: [file join $output_dir utilization_report.txt]"
puts "=========================================================="
exit 0
