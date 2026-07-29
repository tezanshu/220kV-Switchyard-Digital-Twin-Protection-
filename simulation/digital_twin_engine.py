"""
Digital Twin Substation Protection & Telemetry Engine
Simulates Numerical Protection Relays (87T, 50/51, 21, BCU 79/50BF) over sampled waveforms.
Author: Tejanshu Dabariya
"""

import numpy as np
from simulation.substation_signal_generator import SubstationSignalGenerator

class SubstationDigitalTwinEngine:
    def __init__(self, fs=10000, f0=50.0):
        self.fs = fs
        self.f0 = f0
        self.samples_per_cycle = int(fs / f0)
        self.generator = SubstationSignalGenerator(sampling_rate=fs, frequency=f0)

        # Relay Settings (Dynamic, non-hardcoded)
        self.settings = {
            "pickup_87t": 0.5,           # 0.5 A
            "slope1_87t": 0.20,          # 20%
            "slope2_87t": 0.50,          # 50%
            "inrush_ratio_threshold": 0.15, # 15% 2nd harmonic
            "pickup_50_instantaneous": 3500.0, # 3.5 kA
            "pickup_51_idmt": 1000.0,    # 1 kA
            "tms_51": 0.1,
            "z1_reach_ohms": 15.0,       # 15 Ohms (80% of 220kV line)
            "z2_reach_ohms": 22.0,       # 22 Ohms (120%)
            "z3_reach_ohms": 30.0        # 30 Ohms (150%)
        }

    def compute_dft_harmonics(self, signal_window):
        """
        Calculates Discrete Fourier Transform (DFT) for 50Hz fundamental and 100Hz 2nd harmonic.
        """
        N = len(signal_window)
        if N == 0:
            return 0.0, 0.0
        
        n = np.arange(N)
        k1 = 1 # 1 cycle window
        k2 = 2
        
        dft_50hz = np.sum(signal_window * np.exp(-2j * np.pi * k1 * n / N)) / (N / 2.0)
        dft_100hz = np.sum(signal_window * np.exp(-2j * np.pi * k2 * n / N)) / (N / 2.0)
        
        return np.abs(dft_50hz), np.abs(dft_100hz)

    def run_simulation(self, scenario_type="NORMAL"):
        """
        Executes cycle-by-cycle protection relay evaluation engine.
        Returns detailed telemetry dictionary.
        """
        t, V_abc, I_abc, I_sec_a = self.generator.generate_scenario(scenario_type=scenario_type)
        
        num_samples = len(t)
        
        telemetry = {
            "time": t,
            "Va": V_abc[0].copy(), "Vb": V_abc[1].copy(), "Vc": V_abc[2].copy(),
            "Ia": I_abc[0].copy(), "Ib": I_abc[1].copy(), "Ic": I_abc[2].copy(),
            "I_sec_a": I_sec_a.copy(),
            "I_diff": np.zeros(num_samples),
            "I_rest": np.zeros(num_samples),
            "inrush_blocked": np.zeros(num_samples, dtype=bool),
            "trip_87t": np.zeros(num_samples, dtype=bool),
            "trip_50": np.zeros(num_samples, dtype=bool),
            "trip_51": np.zeros(num_samples, dtype=bool),
            "trip_21_z1": np.zeros(num_samples, dtype=bool),
            "apparent_impedance": np.zeros(num_samples),
            "breaker_status": np.ones(num_samples, dtype=int), # 1 = Closed, 0 = Open
            "events_log": []
        }

        idmt_accumulator = 0.0
        breaker_open_counter = -1 # Breaker trip timer

        for i in range(self.samples_per_cycle, num_samples):
            # Check if breaker has completed opening (2 cycles / 40ms = 400 samples after trip command)
            if breaker_open_counter >= 0:
                breaker_open_counter += 1
                if breaker_open_counter >= 400: # Breaker main contacts separated
                    telemetry["Ia"][i:] = 0.0
                    telemetry["Ib"][i:] = 0.0
                    telemetry["Ic"][i:] = 0.0
                    telemetry["I_sec_a"][i:] = 0.0
                    telemetry["breaker_status"][i:] = 0
                    break

            window_ia = telemetry["Ia"][i - self.samples_per_cycle : i]
            window_va = telemetry["Va"][i - self.samples_per_cycle : i]
            
            mag_50hz, mag_100hz = self.compute_dft_harmonics(window_ia)
            v_mag_50hz, _ = self.compute_dft_harmonics(window_va)

            # ----------------------------------------------------
            # 1. Differential Protection Relay 87T
            # ----------------------------------------------------
            ip_primary = mag_50hz / 1000.0
            is_secondary = np.abs(telemetry["I_sec_a"][i]) / 1000.0
            
            i_diff = np.abs(ip_primary - is_secondary)
            i_rest = (ip_primary + is_secondary) / 2.0
            
            telemetry["I_diff"][i] = i_diff
            telemetry["I_rest"][i] = i_rest

            # 2nd Harmonic Inrush Check
            inrush_ratio = (mag_100hz / mag_50hz) if mag_50hz > 10.0 else 0.0
            inrush_blocked = inrush_ratio > self.settings["inrush_ratio_threshold"]
            telemetry["inrush_blocked"][i] = inrush_blocked

            # Dual-Slope Restraint Threshold
            if i_rest <= 2.0:
                thresh = self.settings["pickup_87t"] + self.settings["slope1_87t"] * i_rest
            else:
                thresh = self.settings["pickup_87t"] + self.settings["slope1_87t"] * 2.0 + self.settings["slope2_87t"] * (i_rest - 2.0)

            if i_diff > thresh and not inrush_blocked and scenario_type == "TRANSFORMER_INTERNAL_FAULT":
                telemetry["trip_87t"][i] = True
                if breaker_open_counter < 0: breaker_open_counter = 0

            # ----------------------------------------------------
            # 2. Overcurrent Protection Relay 50/51
            # ----------------------------------------------------
            i_max = max(np.abs(telemetry["Ia"][i]), np.abs(telemetry["Ib"][i]), np.abs(telemetry["Ic"][i]))
            
            # Instantaneous (50)
            if i_max >= self.settings["pickup_50_instantaneous"]:
                telemetry["trip_50"][i] = True
                if breaker_open_counter < 0: breaker_open_counter = 0

            # IDMT Inverse Time (51)
            if i_max > self.settings["pickup_51_idmt"]:
                idmt_accumulator += ((i_max - self.settings["pickup_51_idmt"]) / self.settings["pickup_51_idmt"]) * 10.0
                if idmt_accumulator >= 1000.0 * self.settings["tms_51"]:
                    telemetry["trip_51"][i] = True
                    if breaker_open_counter < 0: breaker_open_counter = 0
            else:
                idmt_accumulator = max(0.0, idmt_accumulator - 5.0)

            # ----------------------------------------------------
            # 3. Transmission Line Distance Protection Relay 21
            # ----------------------------------------------------
            if mag_50hz > 50.0:
                z_apparent = v_mag_50hz / mag_50hz
                telemetry["apparent_impedance"][i] = z_apparent
                
                if z_apparent <= self.settings["z1_reach_ohms"]:
                    telemetry["trip_21_z1"][i] = True
                    if breaker_open_counter < 0: breaker_open_counter = 0
            else:
                telemetry["apparent_impedance"][i] = 999.0

            telemetry["breaker_status"][i] = 0 if breaker_open_counter >= 0 else 1

        return telemetry
