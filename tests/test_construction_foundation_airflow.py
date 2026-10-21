"""Geometry-scaled garage leakage must match the source, independently of dwelling ACH."""
import importlib.util
import unittest


class FoundationAirflowTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_airflow'))
        from scripts import construction_foundation_airflow
        return construction_foundation_airflow

    def test_sg_geometry_scaling_and_explicit_unknowns(self):
        m=self.module()
        p={'ela_volume_coefficient_s_m':.075,'stack_height_coefficient_m_s2_K':.005,
           'wind_coefficient_scale':.01,'wind_reference_height_m':10,'wind_height_exponent':.5}
        result=m.garage_coefficients(p,volume_m3=100,height_m=3,foundation_top_m=1,exterior_ach50_per_s=5/3600)
        self.assertAlmostEqual(result['effective_leakage_area_m2'],.010416666666666666)
        self.assertAlmostEqual(result['stack_coefficient_m2_s2_K'],.015)
        self.assertAlmostEqual(result['wind_coefficient'],.006324555320336759)
        with self.assertRaises(ValueError):m.garage_coefficients(p,volume_m3=100,height_m=None,foundation_top_m=1,exterior_ach50_per_s=5/3600)


if __name__=='__main__':unittest.main()
