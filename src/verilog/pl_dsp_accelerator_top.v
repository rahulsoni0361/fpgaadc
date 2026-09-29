// pl_dsp_accelerator_top.v
// Top-Level AXI-Lite Hardware DSP Accelerator & Hardware Timer for PYNQ-Z2
// Interfaces ARM Cortex-A9 PS to 16-Tap Parallel DSP48E1 FIR Filter
// Provides 64-bit nanosecond cycle timers to prove PL determinism vs PS jitter.

`timescale 1ns / 1ps

module pl_dsp_accelerator_top #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 6
)(
    // AXI4-Lite Clock & Reset
    input  wire                              s_axi_aclk,
    input  wire                              s_axi_aresetn,

    // AXI4-Lite Slave Interface
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire                              s_axi_awvalid,
    output wire                              s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [3:0]                        s_axi_wstrb,
    input  wire                              s_axi_wvalid,
    output wire                              s_axi_wready,
    output wire [1:0]                        s_axi_bresp,
    output wire                              s_axi_bvalid,
    input  wire                              s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire                              s_axi_arvalid,
    output wire                              s_axi_arready,
    output wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output wire [1:0]                        s_axi_rresp,
    output wire                              s_axi_rvalid,
    input  wire                              s_axi_rready,

    // Direct Hardware ADC Stream Port (Optional external ADC header)
    input  wire                              ext_adc_valid,
    input  wire signed [15:0]                ext_adc_data,

    // Interrupt to PS
    output wire                              irq_sample_ready
);

    // 64-Bit Nanosecond Hardware Cycle Counter (100 MHz clock = 10.0 ns / tick)
    reg [63:0] hw_cycle_counter;
    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn)
            hw_cycle_counter <= 64'd0;
        else
            hw_cycle_counter <= hw_cycle_counter + 64'd1;
    end

    // Internal Registers (Memory Mapped via AXI-Lite)
    // 0x00: Control Register (Bit 0: Enable, Bit 1: Reset Accumulator, Bit 2: Source Select)
    // 0x04: Status Register (Bit 0: Output Valid, Bit 1: FIFO Full, Bit 2: Overrun)
    // 0x08: ADC Sample Input (Write raw 16-bit signed sample)
    // 0x0C: Filtered Output Sample (Read 16-bit filtered sample)
    // 0x10: Total Samples Processed (32-bit counter)
    // 0x14: Accumulator Low 32-bit
    // 0x18: Cycle Timer Low 32-bit (Nanoseconds = cycles * 10)
    // 0x1C: Cycle Timer High 32-bit
    reg [31:0] reg_ctrl;
    reg [31:0] reg_status;
    reg [31:0] reg_adc_in;
    reg [31:0] reg_sample_count;
    reg        soft_sample_valid;

    wire        dsp_valid_out;
    wire signed [15:0] dsp_data_out;
    wire signed [23:0] dsp_accum_out;

    // Multiplex between external ADC stream and soft AXI register write
    wire                  active_sample_valid = reg_ctrl[2] ? ext_adc_valid : soft_sample_valid;
    wire signed [15:0]    active_sample_data  = reg_ctrl[2] ? ext_adc_data  : reg_adc_in[15:0];

    // Instantiate Parallel 16-Tap FIR Accelerator
    pl_fir_filter_16 fir_inst (
        .clk             (s_axi_aclk),
        .resetn          (s_axi_aresetn && !reg_ctrl[1]),
        .sample_valid_in (active_sample_valid && reg_ctrl[0]),
        .sample_data_in  (active_sample_data),
        .sample_valid_out(dsp_valid_out),
        .sample_data_out (dsp_data_out),
        .accumulator_out (dsp_accum_out)
    );

    // Track statistics in hardware fabric
    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            reg_sample_count <= 32'd0;
            reg_status       <= 32'd0;
        end else begin
            if (dsp_valid_out) begin
                reg_sample_count <= reg_sample_count + 32'd1;
                reg_status[0]    <= 1'b1; // Output valid latch
            end
            if (soft_sample_valid) begin
                soft_sample_valid <= 1'b0; // Auto-clear trigger pulse
            end
        end
    end

    assign irq_sample_ready = dsp_valid_out;

    // Simple AXI-Lite Slave Logic
    reg awready_reg, wready_reg, arready_reg, rvalid_reg, bvalid_reg;
    reg [C_S_AXI_DATA_WIDTH-1:0] rdata_reg;

    assign s_axi_awready = awready_reg;
    assign s_axi_wready  = wready_reg;
    assign s_axi_arready = arready_reg;
    assign s_axi_rvalid  = rvalid_reg;
    assign s_axi_bvalid  = bvalid_reg;
    assign s_axi_rdata   = rdata_reg;
    assign s_axi_bresp   = 2'b00;
    assign s_axi_rresp   = 2'b00;

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            awready_reg <= 1'b0;
            wready_reg  <= 1'b0;
            bvalid_reg  <= 1'b0;
            arready_reg <= 1'b0;
            rvalid_reg  <= 1'b0;
            reg_ctrl    <= 32'h00000001; // Enable by default
            reg_adc_in  <= 32'd0;
            soft_sample_valid <= 1'b0;
        end else begin
            // Write handshake
            if (!awready_reg && s_axi_awvalid && s_axi_wvalid) begin
                awready_reg <= 1'b1;
                wready_reg  <= 1'b1;
                case (s_axi_awaddr[5:2])
                    4'h0: reg_ctrl   <= s_axi_wdata;
                    4'h2: begin
                        reg_adc_in        <= s_axi_wdata;
                        soft_sample_valid <= 1'b1; // Trigger hardware FIR execution
                    end
                endcase
            end else begin
                awready_reg <= 1'b0;
                wready_reg  <= 1'b0;
            end

            if (awready_reg && s_axi_wvalid && !bvalid_reg)
                bvalid_reg <= 1'b1;
            else if (s_axi_bready && bvalid_reg)
                bvalid_reg <= 1'b0;

            // Read handshake
            if (!arready_reg && s_axi_arvalid) begin
                arready_reg <= 1'b1;
                rvalid_reg  <= 1'b1;
                case (s_axi_araddr[5:2])
                    4'h0: rdata_reg <= reg_ctrl;
                    4'h1: rdata_reg <= reg_status;
                    4'h2: rdata_reg <= reg_adc_in;
                    4'h3: rdata_reg <= {16'h0000, dsp_data_out}; // Filtered output
                    4'h4: rdata_reg <= reg_sample_count;
                    4'h5: rdata_reg <= {8'h00, dsp_accum_out};
                    4'h6: rdata_reg <= hw_cycle_counter[31:0];
                    4'h7: rdata_reg <= hw_cycle_counter[63:32];
                    default: rdata_reg <= 32'hDEADBEEF;
                endcase
            end else begin
                arready_reg <= 1'b0;
                if (s_axi_rready && rvalid_reg)
                    rvalid_reg <= 1'b0;
            end
        end
    end

endmodule
