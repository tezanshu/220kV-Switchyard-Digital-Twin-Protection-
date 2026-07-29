"""
Substation 3-Phase Waveform & Fault Signal Generator
Target: 220kV / 66kV Power Grid & Switchyard Substation Digital Twin
Author: Tejanshu Dabariya
"""

import numpy as np

class SubstationSignalGenerator:
    def __init__(self, sampling_rate=10000, frequency=50.0, base_voltage_kv=220.0, base_current_a=500.0):
        self.fs = sampling_rate
        self.f0 = frequency
        self.v_base = base_voltage_kv * 1000.0 / np.sqrt(3) # Phase-to-neutral peak = V_LL_rms * sqrt(2)/sqrt(3)
        self.i_base = base_current_a * np.sqrt(2)
        self.omega = 2 * np.pi * self.f0

    def generate_scenario(self, scenario_type="NORMAL", duration_sec=0.2, fault_onset_sec=0.05):
        """
        Generates 3-Phase Voltage and Current Waveforms for various switchyard scenarios.
        Returns: (t, V_abc, I_abc, I_secondary_transformer)
        """
        t = np.linspace(0, duration_sec, int(self.fs * duration_sec))
        
        # Fundamental Phase Angles (120 degrees apart)
        phi_a = 0.0
        phi_b = -2 * np.pi / 3
        phi_c = 2 * np.pi / 3

        # Base Voltage (Va, Vb, Vc)
        Va = self.v_base * np.sin(self.omega * t + phi_a)
        Vb = self.v_base * np.sin(self.omega * t + phi_b)
        Vc = self.v_base * np.sin(self.omega * t + phi_c)

        # Base Current (Ia, Ib, Ic)
        Ia = self.i_base * np.sin(self.omega * t + phi_a - 0.2) # Lagging pf=0.98
        Ib = self.i_base * np.sin(self.omega * t + phi_b - 0.2)
        Ic = self.i_base * np.sin(self.omega * t + phi_c - 0.2)

        # HV/LV Transformer Ratio (220kV to 66kV -> N = 3.33)
        I_sec_a = Ia / 3.33

        if scenario_type == "NORMAL":
            pass

        elif scenario_type == "SLG_FAULT_A":
            # Single Line to Ground Fault on Phase A at t >= fault_onset_sec
            fault_mask = t >= fault_onset_sec
            fault_current_mag = 4500.0 * np.sqrt(2) # 4.5 kA fault
            # DC Offset transient
            dc_decay = np.exp(-(t[fault_mask] - fault_onset_sec) / 0.03)
            Ia[fault_mask] = fault_current_mag * (np.sin(self.omega * (t[fault_mask] - fault_onset_sec) - np.pi/2) + 0.8 * dc_decay)
            Va[fault_mask] *= 0.15 # Voltage dip on faulted phase A

        elif scenario_type == "3PHASE_FAULT":
            # 3-Phase Symmetrical Fault
            fault_mask = t >= fault_onset_sec
            fault_current_mag = 8000.0 * np.sqrt(2) # 8 kA symmetrical fault
            dc_decay = np.exp(-(t[fault_mask] - fault_onset_sec) / 0.04)
            
            Ia[fault_mask] = fault_current_mag * (np.sin(self.omega * t[fault_mask] + phi_a - np.pi/2) + 0.5 * dc_decay)
            Ib[fault_mask] = fault_current_mag * (np.sin(self.omega * t[fault_mask] + phi_b - np.pi/2) + 0.5 * dc_decay)
            Ic[fault_mask] = fault_current_mag * (np.sin(self.omega * t[fault_mask] + phi_c - np.pi/2) + 0.5 * dc_decay)

            Va[fault_mask] *= 0.05
            Vb[fault_mask] *= 0.05
            Vc[fault_mask] *= 0.05

        elif scenario_type == "INRUSH_TRANSFORMER":
            # Transformer Magnetizing Inrush Current (Heavy 2nd harmonic 100Hz)
            inrush_mask = t >= fault_onset_sec
            t_inrush = t[inrush_mask] - fault_onset_sec
            decay = np.exp(-t_inrush / 0.08)
            
            # Inrush waveform = Fundamental (50Hz) + 38% 2nd Harmonic (100Hz) + 15% 3rd Harmonic (150Hz)
            inrush_ia = 3000.0 * decay * (
                np.sin(self.omega * t_inrush) +
                0.38 * np.sin(2 * self.omega * t_inrush + 0.3) +
                0.15 * np.sin(3 * self.omega * t_inrush + 0.6)
            )
            Ia[inrush_mask] += inrush_ia
            # Secondary current does NOT see magnetizing inrush -> High Differential Current!
            I_sec_a[inrush_mask] = (self.i_base / 3.33) * np.sin(self.omega * t[inrush_mask] + phi_a - 0.2)

        elif scenario_type == "TRANSFORMER_INTERNAL_FAULT":
            # Internal Turn-to-Turn Winding Fault on 220kV Transformer
            fault_mask = t >= fault_onset_sec
            Ia[fault_mask] = 5500.0 * np.sqrt(2) * np.sin(self.omega * t[fault_mask] - np.pi/2)
            I_sec_a[fault_mask] = 200.0 * np.sin(self.omega * t[fault_mask])

        elif scenario_type == "CT_SATURATION":
            # High fault current causing CT Core Saturation (Clipped waveform)
            fault_mask = t >= fault_onset_sec
            raw_fault = 10000.0 * np.sin(self.omega * t[fault_mask] - np.pi/2)
            clip_threshold = 4000.0
            Ia[fault_mask] = np.clip(raw_fault, -clip_threshold, clip_threshold)

        V_abc = np.vstack([Va, Vb, Vc])
        I_abc = np.vstack([Ia, Ib, Ic])
        
        return t, V_abc, I_abc, I_sec_a
