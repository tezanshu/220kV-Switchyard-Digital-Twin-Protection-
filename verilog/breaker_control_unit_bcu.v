// ============================================================================
// File: verilog/breaker_control_unit_bcu.v
// Module: breaker_control_unit_bcu
// Description: Circuit Breaker Control Unit (BCU) with Auto-Recloser (79),
//              Trip Circuit Supervision (TCS), and Breaker Failure (50BF).
// Target Application: 220kV Switchyard SF6 Circuit Breaker Control
// Author: Tejanshu Dabariya
// ============================================================================

`timescale 1ns / 1ps

module breaker_control_unit_bcu (
    input  wire        clk,
    input  wire        reset_n,
    
    // Protection & SCADA Inputs
    input  wire        trip_87t_in,
    input  wire        trip_50_51_in,
    input  wire        trip_21_in,
    input  wire        scada_manual_open,
    input  wire        scada_manual_close,
    
    // Status Feedback Signals from Substation Hardware
    input  wire        breaker_aux_nc,       // 52a contact (1 when breaker closed)
    input  wire        breaker_aux_no,       // 52b contact (1 when breaker open)
    input  wire        trip_circuit_healthy, // TCS healthy signal
    input  wire        sf6_gas_pressure_ok,  // SF6 gas pressure lock
    
    // Physical Breaker Actuation Outputs
    output reg         trip_coil_energize,
    output reg         close_coil_energize,
    output reg         breaker_status_closed,
    output reg         breaker_status_open,
    output reg         breaker_lockout,
    output reg         breaker_failure_50bf  // Busbar backup trip trigger
);

    reg [15:0] bfu_counter;
    reg [15:0] reclose_counter;
    reg        reclose_attempted;
    wire       any_protective_trip;

    assign any_protective_trip = trip_87t_in | trip_50_51_in | trip_21_in | scada_manual_open;

    // Breaker Auxiliary Status Update
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            breaker_status_closed <= 1'b1;
            breaker_status_open   <= 1'b0;
        end else begin
            breaker_status_closed <= breaker_aux_nc;
            breaker_status_open   <= breaker_aux_no;
        end
    end

    // Breaker Actuation & Auto-Reclose (79) FSM
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            trip_coil_energize  <= 1'b0;
            close_coil_energize <= 1'b0;
            breaker_lockout     <= 1'b0;
            reclose_counter     <= 0;
            reclose_attempted   <= 1'b0;
        end else if (sf6_gas_pressure_ok && trip_circuit_healthy) begin
            
            if (any_protective_trip && !breaker_lockout) begin
                trip_coil_energize  <= 1'b1;
                close_coil_energize <= 1'b0;
                
                // If it's a line fault (21 trip), initiate 1-shot Auto-Reclose timer
                if (trip_21_in && !reclose_attempted) begin
                    reclose_counter <= reclose_counter + 1;
                    if (reclose_counter >= 16'd1000) begin // 1.0s dead time
                        close_coil_energize <= 1'b1;
                        trip_coil_energize  <= 1'b0;
                        reclose_attempted   <= 1'b1;
                    end
                end else if (reclose_attempted && any_protective_trip) begin
                    // Permanent fault after auto-reclose -> LOCKOUT
                    breaker_lockout <= 1'b1;
                end
            end else if (scada_manual_close && !breaker_lockout) begin
                close_coil_energize <= 1'b1;
                trip_coil_energize  <= 1'b0;
                reclose_attempted   <= 1'b0;
            end else begin
                trip_coil_energize  <= 1'b0;
                close_coil_energize <= 1'b0;
            end
            
        end
    end

    % Breaker Failure Protection (50BF): Detect if current flows >100ms after trip command
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            bfu_counter          <= 0;
            breaker_failure_50bf <= 1'b0;
        end else begin
            if (trip_coil_energize && breaker_status_closed) begin
                bfu_counter <= bfu_counter + 1;
                if (bfu_counter >= 16'd100) // Breaker failed to clear in 100ms
                    breaker_failure_50bf <= 1'b1;
            end else begin
                bfu_counter          <= 0;
                breaker_failure_50bf <= 1'b0;
            end
        end
    end

endmodule
