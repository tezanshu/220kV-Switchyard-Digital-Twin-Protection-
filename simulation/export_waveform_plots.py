"""
Substation Waveform Visualizer & PNG Generator
Generates publication-quality figures for README documentation and artifacts.
Author: Tejanshu Dabariya
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from simulation.digital_twin_engine import SubstationDigitalTwinEngine

def generate_all_plots(output_dir="docs/images"):
    os.makedirs(output_dir, exist_ok=True)
    engine = SubstationDigitalTwinEngine()

    # 1. Plot 1: SLG Fault Waveform & Breaker Clearance
    print("Generating SLG Fault Telemetry Plot...")
    telemetry_slg = engine.run_simulation("SLG_FAULT_A")
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle("220kV Substation Single Line-to-Ground (SLG) Fault & Relay Clearance", fontsize=14, fontweight='bold')
    
    t_ms = telemetry_slg["time"] * 1000.0
    
    # Voltage Waveforms
    ax1.plot(t_ms, telemetry_slg["Va"]/1000.0, label="Va (kV)", color='red')
    ax1.plot(t_ms, telemetry_slg["Vb"]/1000.0, label="Vb (kV)", color='yellow', linestyle='--')
    ax1.plot(t_ms, telemetry_slg["Vc"]/1000.0, label="Vc (kV)", color='blue', linestyle=':')
    ax1.set_ylabel("Voltage (kV)")
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc="upper right")
    ax1.set_title("3-Phase Busbar Voltage (PT)")

    # Current Waveforms
    ax2.plot(t_ms, telemetry_slg["Ia"], label="Ia (A)", color='red')
    ax2.plot(t_ms, telemetry_slg["Ib"], label="Ib (A)", color='orange')
    ax2.plot(t_ms, telemetry_slg["Ic"], label="Ic (A)", color='blue')
    ax2.set_ylabel("Current (A)")
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(loc="upper right")
    ax2.set_title("3-Phase Feeder Current (CT)")

    # Breaker Status & Relay Signals
    ax3.plot(t_ms, telemetry_slg["breaker_status"], label="Breaker 52a Status (1=Closed, 0=Open)", color='green', linewidth=2)
    ax3.plot(t_ms, telemetry_slg["trip_50"], label="Relay 50 Trip Signal", color='magenta', linestyle='--')
    ax3.set_xlabel("Time (ms)")
    ax3.set_ylabel("Digital Status")
    ax3.set_yticks([0, 1])
    ax3.grid(True, linestyle='--', alpha=0.6)
    ax3.legend(loc="upper right")
    ax3.set_title("Circuit Breaker Status & Relay Trip Command")

    plt.tight_layout()
    plot1_path = os.path.join(output_dir, "slg_fault_clearance.png")
    plt.savefig(plot1_path, dpi=300)
    plt.close()
    print(f"Saved: {plot1_path}")

    # 2. Plot 2: 87T Dual-Slope Differential & Inrush Restraint
    print("Generating 87T Differential Protection Plot...")
    telemetry_inrush = engine.run_simulation("INRUSH_TRANSFORMER")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle("Transformer 87T Differential Protection: Magnetizing Inrush Blocking", fontsize=14, fontweight='bold')
    
    ax1.plot(t_ms, telemetry_inrush["Ia"], label="Primary CT Current (HV)", color='crimson')
    ax1.set_ylabel("Current (A)")
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    ax1.set_title("HV Transformer Primary Current during Energization Inrush")

    ax2.plot(t_ms, telemetry_inrush["I_diff"], label="Differential Current (I_diff)", color='purple', linewidth=2)
    ax2.plot(t_ms, telemetry_inrush["inrush_blocked"] * np.max(telemetry_inrush["I_diff"]), 
             label="2nd Harmonic Inrush Block (Active)", color='darkgreen', linestyle='--', alpha=0.7)
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Current (A)")
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
    ax2.set_title("87T Differential Current & 2nd Harmonic Restraint Blocking Signal")

    plt.tight_layout()
    plot2_path = os.path.join(output_dir, "transformer_87t_inrush.png")
    plt.savefig(plot2_path, dpi=300)
    plt.close()
    print(f"Saved: {plot2_path}")

    # 3. Plot 3: Mho Distance Protection Circle Diagram (R-X Plane)
    print("Generating 21 Distance Mho Diagram...")
    fig, ax = plt.subplots(figsize=(7, 7))
    
    # Plot Mho Circles
    z1 = 12.0
    z2 = 18.0
    z3 = 25.0
    
    theta = np.linspace(0, 2*np.pi, 200)
    # Mho circle centered at (Z/2 * cos(75), Z/2 * sin(75))
    angle = np.radians(75) # Line characteristic angle
    
    for z_val, label, col in zip([z1, z2, z3], ["Zone 1 (80%)", "Zone 2 (120%)", "Zone 3 (150%)"], ["red", "orange", "blue"]):
        r_c = z_val / 2.0
        x_c = r_c * np.cos(angle)
        y_c = r_c * np.sin(angle)
        
        x_circle = x_c + r_c * np.cos(theta)
        y_circle = y_c + r_c * np.sin(theta)
        ax.plot(x_circle, y_circle, label=f"Mho {label} - Reach {z_val}Ω", color=col, linewidth=2)

    # Impedance trajectory during fault
    z_traj_r = [20.0, 18.0, 14.0, 9.0, 4.0]
    z_traj_x = [30.0, 25.0, 18.0, 11.0, 5.0]
    ax.plot(z_traj_r, z_traj_x, 'ro--', label="Apparent Impedance Trajectory", linewidth=2)
    ax.annotate("Fault Inception", (z_traj_r[0], z_traj_x[0]), xytext=(z_traj_r[0]+2, z_traj_x[0]+2),
                arrowprops=dict(facecolor='black', shrink=0.05))
    ax.annotate("Zone 1 TRIP", (z_traj_r[-1], z_traj_x[-1]), xytext=(z_traj_r[-1]+2, z_traj_x[-1]-2),
                arrowprops=dict(facecolor='red', shrink=0.05))

    ax.set_xlabel("Resistance R (Ohms)", fontweight='bold')
    ax.set_ylabel("Reactance X (Ohms)", fontweight='bold')
    ax.set_title("ANSI 21 Mho Distance Relay Characteristic (R-X Plane)", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.axhline(0, color='black', linewidth=1)
    ax.axvline(0, color='black', linewidth=1)
    ax.legend(loc="upper left")
    ax.set_aspect('equal', 'box')

    plt.tight_layout()
    plot3_path = os.path.join(output_dir, "mho_distance_rx_plane.png")
    plt.savefig(plot3_path, dpi=300)
    plt.close()
    print(f"Saved: {plot3_path}")

    return [plot1_path, plot2_path, plot3_path]

if __name__ == "__main__":
    generate_all_plots()
