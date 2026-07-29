// ============================================================================
// File: verilog/overcurrent_relay_50_51.v
// Module: overcurrent_relay_50_51
// Description: Synthesizable Verilog Numerical Overcurrent Relay implementing
//              Instantaneous (50) and IEC 60255 IDMT (51) Time-Overcurrent curves.
// Target Application: 220kV Feeder / Busbar / Line Protection
// Author: Tejanshu Dabariya
// ============================================================================

`timescale 1ns / 1ps

module overcurrent_relay_50_51 #(
    parameter DATA_WIDTH = 16
)(
    input  wire                  clk,
    input  wire                  reset_n,
    input  wire                  enable,
    
    // Configurable Settings (Dynamic)
    input  wire [DATA_WIDTH-1:0] i_pickup_51,    // IDMT Pickup current I_s (scaled x1000)
    input  wire [DATA_WIDTH-1:0] i_pickup_50,    // Instantaneous Pickup current I_inst (scaled x1000)
    input  wire [DATA_WIDTH-1:0] tms,            // Time Multiplier Setting (TMS x1000)
    input  wire [1:0]            curve_type,     // 00: Standard Inv, 01: Very Inv, 10: Extremely Inv, 11: Definite Time
    
    // Sampled Phase Currents (Magnitudes, x1000)
    input  wire [DATA_WIDTH-1:0] i_phase_a,
    input  wire [DATA_WIDTH-1:0] i_phase_b,
    input  wire [DATA_WIDTH-1:0] i_phase_c,
    
    // Relay Outputs
    output reg                   trip_50_instantaneous,
    output reg                   trip_51_idmt,
    output reg                   master_trip_oc,
    output reg  [31:0]           accumulator_val
);

    // Max current selection
    reg [DATA_WIDTH-1:0] max_current;
    reg [31:0]           idmt_accumulator;
    reg [31:0]           trip_delay_target;

    // 1. Determine Maximum Phase Current
    always @(*) begin
        if (i_phase_a >= i_phase_b && i_phase_a >= i_phase_c)
            max_current = i_phase_a;
        else if (i_phase_b >= i_phase_a && i_phase_b >= i_phase_c)
            max_current = i_phase_b;
        else
            max_current = i_phase_c;
    end

    // 2. Instantaneous Protection (ANSI 50)
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            trip_50_instantaneous <= 1'b0;
        end else if (enable) begin
            if (max_current >= i_pickup_50 && i_pickup_50 > 0)
                trip_50_instantaneous <= 1'b1;
            else
                trip_50_instantaneous <= 1'b0;
        end
    end

    // 3. IDMT Inverse-Time Accumulator Logic (ANSI 51)
    // Computes dynamic integration step based on (I / I_s) ratio
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            idmt_accumulator <= 32'd0;
            trip_51_idmt     <= 1'b0;
            accumulator_val  <= 32'd0;
        end else if (enable) begin
            if (max_current > i_pickup_51 && i_pickup_51 > 0) begin
                // Accumulate integration count towards curve-dependent target
                // Higher current = faster accumulation speed
                case (curve_type)
                    2'b00: idmt_accumulator <= idmt_accumulator + ((max_current - i_pickup_51) * 10 / i_pickup_51) + 1; // Standard Inverse
                    2'b01: idmt_accumulator <= idmt_accumulator + (((max_current - i_pickup_51) * (max_current - i_pickup_51)) / i_pickup_51) + 1; // Very Inverse
                    2'b10: idmt_accumulator <= idmt_accumulator + (((max_current - i_pickup_51) ** 3) / (i_pickup_51 ** 2)) + 1; // Extremely Inverse
                    2'b11: idmt_accumulator <= idmt_accumulator + 10; // Definite Time
                endcase

                // Target threshold proportional to TMS
                if (idmt_accumulator >= (32'd100000 * tms / 1000)) begin
                    trip_51_idmt <= 1'b1;
                end
            end else begin
                // Reset accumulator when current drops below pickup (disk reset behavior)
                if (idmt_accumulator > 50)
                    idmt_accumulator <= idmt_accumulator - 50;
                else
                    idmt_accumulator <= 0;

                trip_51_idmt <= 1'b0;
            end
            accumulator_val <= idmt_accumulator;
        end
    end

    // 4. Combined Master Overcurrent Trip Output
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            master_trip_oc <= 1'b0;
        end else if (enable) begin
            master_trip_oc <= trip_50_instantaneous | trip_51_idmt;
        end
    end

endmodule
