// ============================================================================
// File: verilog/differential_relay_87t.v
// Module: differential_relay_87t
// Description: Synthesizable Verilog implementation of a Numerical 
//              Transformer Differential Relay (87T) with Dual-Slope 
//              Percentage Restraint & 2nd Harmonic Inrush Blocking.
// Target Application: 220kV / 66kV Power Transformer Protection in Substation
// Author: Tejanshu Dabariya
// ============================================================================

`timescale 1ns / 1ps

module differential_relay_87t #(
    parameter DATA_WIDTH      = 16,
    parameter DEFAULT_PICKUP  = 16'd500,   % 0.5A pickup (scaled x1000)
    parameter DEFAULT_SLOPE1  = 16'd200,   % 20% Slope 1
    parameter DEFAULT_SLOPE2  = 16'd500,   % 50% Slope 2
    parameter BREAK_POINT     = 16'd2000,  % 2.0A Restraint breakpoint
    parameter INRUSH_RATIO    = 16'd150    % 15% 2nd Harmonic restraint ratio
)(
    input  wire                  clk,
    input  wire                  reset_n,
    input  wire                  enable,
    
    // Configurable Settings (Dynamic, non-hardcoded)
    input  wire [DATA_WIDTH-1:0] i_pickup,
    input  wire [DATA_WIDTH-1:0] slope1,        // % x1000
    input  wire [DATA_WIDTH-1:0] slope2,        // % x1000
    input  wire [DATA_WIDTH-1:0] break_point,
    input  wire [DATA_WIDTH-1:0] inrush_threshold,
    
    // CT Secondary Currents (Magnitude & Harmonic Components, scaled x1000)
    input  wire [DATA_WIDTH-1:0] i_primary_mag,      // HV CT current magnitude
    input  wire [DATA_WIDTH-1:0] i_secondary_mag,    // LV CT current magnitude
    input  wire [DATA_WIDTH-1:0] i_fund_mag,         // Fundamental 50Hz magnitude
    input  wire [DATA_WIDTH-1:0] i_2nd_harm_mag,     // 2nd Harmonic 100Hz magnitude
    input  wire                  buchholz_trip_in,   // External mechanical Buchholz gas trip
    
    // Outputs
    output reg                   trip_87t,
    output reg                   inrush_block,
    output reg                   buchholz_trip,
    output reg  [DATA_WIDTH-1:0] i_diff_out,
    output reg  [DATA_WIDTH-1:0] i_rest_out
);

    // Internal Registers
    reg [DATA_WIDTH:0]   i_diff;
    reg [DATA_WIDTH:0]   i_rest;
    reg [31:0]           threshold_calc;
    reg                  internal_fault_cond;

    // 1. Calculate Operating (Differential) and Restraint Currents
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            i_diff     <= 0;
            i_rest     <= 0;
            i_diff_out <= 0;
            i_rest_out <= 0;
        end else if (enable) begin
            // I_diff = |I_primary - I_secondary|
            if (i_primary_mag >= i_secondary_mag)
                i_diff <= i_primary_mag - i_secondary_mag;
            else
                i_diff <= i_secondary_mag - i_primary_mag;
                
            // I_rest = (I_primary + I_secondary) / 2
            i_rest <= (i_primary_mag + i_secondary_mag) >> 1;

            i_diff_out <= i_diff[DATA_WIDTH-1:0];
            i_rest_out <= i_rest[DATA_WIDTH-1:0];
        end
    end

    // 2. 2nd Harmonic Inrush Detection Logic
    // Inrush condition: (I_2nd_harm / I_fund) > inrush_threshold
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            inrush_block <= 1'b0;
        end else if (enable) begin
            if (i_fund_mag > 0 && ((i_2nd_harm_mag * 1000) / i_fund_mag) > inrush_threshold)
                inrush_block <= 1'b1;
            else
                inrush_block <= 1'b0;
        end
    end

    // 3. Dual-Slope Percentage Restraint Evaluation
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            threshold_calc      <= 0;
            internal_fault_cond <= 1'b0;
        end else if (enable) begin
            if (i_rest <= break_point) begin
                // Region 1: Thresh = I_pickup + (slope1 * I_rest) / 1000
                threshold_calc <= i_pickup + ((slope1 * i_rest) / 1000);
            end else begin
                // Region 2: Thresh = I_pickup + (slope1 * Break) / 1000 + (slope2 * (I_rest - Break)) / 1000
                threshold_calc <= i_pickup + ((slope1 * break_point) / 1000) + 
                                  ((slope2 * (i_rest - break_point)) / 1000);
            end

            if (i_diff > threshold_calc)
                internal_fault_cond <= 1'b1;
            else
                internal_fault_cond <= 1'b0;
        end
    end

    // 4. Master Trip Output Assignment
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            trip_87t      <= 1'b0;
            buchholz_trip <= 1'b0;
        end else if (enable) begin
            buchholz_trip <= buchholz_trip_in;
            
            // Trip if (Internal Fault AND NOT Inrush Blocked) OR Buchholz Mechanical Trip
            if ((internal_fault_cond && !inrush_block) || buchholz_trip_in)
                trip_87t <= 1'b1;
            else
                trip_87t <= 1'b0;
        end
    end

endmodule
