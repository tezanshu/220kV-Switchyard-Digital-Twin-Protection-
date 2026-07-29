// ============================================================================
// File: verilog/distance_protection_21.v
// Module: distance_protection_21
// Description: Synthesizable Verilog 3-Zone Mho Transmission Line Distance Relay (ANSI 21)
// Target Application: 220kV Overhead Transmission Line Protection
// Author: Tejanshu Dabariya
// ============================================================================

`timescale 1ns / 1ps

module distance_protection_21 #(
    parameter DATA_WIDTH = 16
)(
    input  wire                  clk,
    input  wire                  reset_n,
    input  wire                  enable,
    
    // Zone Impedance Settings (scaled x100 in Ohms)
    input  wire [DATA_WIDTH-1:0] z1_reach,       // Zone 1 Reach (Instantaneous, 80% line)
    input  wire [DATA_WIDTH-1:0] z2_reach,       // Zone 2 Reach (Delayed ~300ms, 120% line)
    input  wire [DATA_WIDTH-1:0] z3_reach,       // Zone 3 Reach (Delayed ~500ms, 150% line)
    
    // Sampled Voltage and Current Magnitudes
    input  wire [DATA_WIDTH-1:0] v_magnitude,    // PT Volts (x100)
    input  wire [DATA_WIDTH-1:0] i_magnitude,    // CT Amps (x100)
    
    // Trip Outputs
    output reg                   trip_zone1,
    output reg                   trip_zone2,
    output reg                   trip_zone3,
    output reg                   master_trip_21,
    output reg  [DATA_WIDTH-1:0] z_calculated
);

    reg [31:0]           z_calc;
    reg [15:0]           z2_counter;
    reg [15:0]           z3_counter;

    // 1. Apparent Impedance Calculation: Z = V / I
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            z_calc       <= 32'hFFFF;
            z_calculated <= 16'hFFFF;
        end else if (enable) begin
            if (i_magnitude > 10) begin // Avoid div by zero
                z_calc <= (v_magnitude * 100) / i_magnitude;
                z_calculated <= z_calc[15:0];
            end else begin
                z_calc <= 32'hFFFF;
                z_calculated <= 16'hFFFF;
            end
        end
    end

    // 2. Zone 1 Instantaneous Trip Evaluation (Z < Z1)
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            trip_zone1 <= 1'b0;
        end else if (enable) begin
            if (z_calculated <= z1_reach && i_magnitude > 10)
                trip_zone1 <= 1'b1;
            else
                trip_zone1 <= 1'b0;
        end
    end

    // 3. Zone 2 Delayed Trip Evaluation (Z1 < Z <= Z2)
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            z2_counter <= 0;
            trip_zone2 <= 1'b0;
        end else if (enable) begin
            if (z_calculated > z1_reach && z_calculated <= z2_reach && i_magnitude > 10) begin
                if (z2_counter >= 16'd300) // ~300ms delay cycles
                    trip_zone2 <= 1'b1;
                else
                    z2_counter <= z2_counter + 1;
            end else begin
                z2_counter <= 0;
                trip_zone2 <= 1'b0;
            end
        end
    end

    // 4. Zone 3 Backup Delayed Trip Evaluation (Z2 < Z <= Z3)
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            z3_counter <= 0;
            trip_zone3 <= 1'b0;
        end else if (enable) begin
            if (z_calculated > z2_reach && z_calculated <= z3_reach && i_magnitude > 10) begin
                if (z3_counter >= 16'd500) // ~500ms delay cycles
                    trip_zone3 <= 1'b1;
                else
                    z3_counter <= z3_counter + 1;
            end else begin
                z3_counter <= 0;
                trip_zone3 <= 1'b0;
            end
        end
    end

    // 5. Master Distance Trip Output
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            master_trip_21 <= 1'b0;
        end else if (enable) begin
            master_trip_21 <= trip_zone1 | trip_zone2 | trip_zone3;
        end
    end

endmodule
