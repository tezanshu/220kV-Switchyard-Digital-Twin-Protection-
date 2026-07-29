"""
Automated Protection Relay & Signal Processing Unit Tests
Author: Tejanshu Dabariya
"""

import unittest
import numpy as np
from simulation.digital_twin_engine import SubstationDigitalTwinEngine
from simulation.substation_signal_generator import SubstationSignalGenerator

class TestSubstationRelays(unittest.TestCase):
    def setUp(self):
        self.engine = SubstationDigitalTwinEngine()
        self.generator = SubstationSignalGenerator()

    def test_signal_generator_normal(self):
        t, V_abc, I_abc, I_sec = self.generator.generate_scenario("NORMAL")
        self.assertEqual(len(t), 2000)
        # Phase-to-Neutral Peak Voltage for 220kV grid = 220kV * 1000 / sqrt(3) = 127,017 V
        self.assertAlmostEqual(np.max(V_abc[0]), 127017.0, delta=1000.0)

    def test_instantaneous_overcurrent_50_trip(self):
        telemetry = self.engine.run_simulation("3PHASE_FAULT")
        self.assertTrue(np.any(telemetry["trip_50"]))
        self.assertTrue(np.any(telemetry["breaker_status"] == 0))

    def test_transformer_inrush_restraint_87t(self):
        telemetry = self.engine.run_simulation("INRUSH_TRANSFORMER")
        self.assertTrue(np.any(telemetry["inrush_blocked"]))
        self.assertFalse(np.any(telemetry["trip_87t"]))

    def test_transformer_internal_fault_87t_trip(self):
        telemetry = self.engine.run_simulation("TRANSFORMER_INTERNAL_FAULT")
        self.assertTrue(np.any(telemetry["trip_87t"]))

    def test_distance_relay_zone1_trip(self):
        telemetry = self.engine.run_simulation("SLG_FAULT_A")
        self.assertTrue(np.any(telemetry["trip_21_z1"]))

if __name__ == "__main__":
    unittest.main()
