"""Independent analytical checks of heat-flux signs, boundaries and reduction."""
import cmath
import importlib.util
import math
import unittest


class ThermalEquivalenceTests(unittest.TestCase):
    def implementation(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_equivalence'),
                             'Production thermal reducer is missing')
        from scripts import construction_equivalence
        return construction_equivalence

    def test_homogeneous_wall_analytical_fluxes_across_frequencies(self):
        module = self.implementation()
        # Independent solution T(x)=a*cosh(lambda*x)+b*sinh(lambda*x).
        thickness, conductivity, density, cp = 0.2, 1.4, 2100, 900
        layers = [{'R': thickness / conductivity, 'C': thickness * density * cp}]
        for hours in (1, 6, 24, 72, 168):
            omega = 2 * math.pi / (hours * 3600)
            lam = cmath.sqrt(1j * omega * density * cp / conductivity)
            a = conductivity * lam / cmath.tanh(lam * thickness)
            b = -conductivity * lam / cmath.sinh(lam * thickness)
            for re, ri in ((0, 0), (0.04, 0.13), (0.13, 0.04)):
                y = module.response(layers, hours, (re, ri))
                for te, ti, column in ((1, 0, 0), (0, 1, 1)):
                    f, g = a * te + b * ti, b * te + a * ti
                    determinant = (1 + a * re) * (1 + a * ri) - b * b * re * ri
                    qe = (f * (1 + a * ri) - b * ri * g) / determinant
                    qi = ((1 + a * re) * g - b * re * f) / determinant
                    self.assertLess(abs(y[column] - qe), 1e-10)
                    self.assertLess(abs(y[2 + column] - qi), 1e-10)
                    # Air-film temperature drops use inward heat-flux signs.
                    tse, tsi = te - re * qe, ti - ri * qi
                    self.assertLess(abs(qe - a * tse - b * tsi), 1e-10)
                    self.assertLess(abs(qi - b * tse - a * tsi), 1e-10)

    def test_reversing_layers_and_films_swaps_boundaries_not_flux_sign(self):
        module = self.implementation()
        layers = [{'R': .1, 'C': 90000}, {'R': 2, 'C': 0}, {'R': .3, 'C': 12000}]
        for h in (1, 6, 24, 72, 168):
            a = module.response(layers, h, (.04, .13))
            b = module.response(list(reversed(layers)), h, (.13, .04))
            for actual, expected in zip(a, (b[3], b[2], b[1], b[0])):
                self.assertLess(abs(actual - expected), 1e-10)
        y = module.response([{'R': 2, 'C': 0}], 24)
        self.assertEqual(y, (1/2.17, -1/2.17, -1/2.17, 1/2.17))

    def test_reduce_conserves_reference_u_and_capacity_without_extra_layers(self):
        module = self.implementation()
        sources = [{'weight': .3, 'layers': [{'R': .2, 'C': 120000}, {'R': 1, 'C': 0}]},
                   {'weight': .7, 'layers': [{'R': 3, 'C': 0}, {'R': .1, 'C': 24000}]}]
        result = module.reduce_opaque(sources)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(len(result['layers']), 3)
        target_u = .3/1.37 + .7/3.27
        self.assertAlmostEqual(1/(sum(l['R'] for l in result['layers'])+.17), target_u)
        self.assertAlmostEqual(sum(l['C'] for l in result['layers']), .3*120000+.7*24000)
        self.assertIn('normalized_response_rms', result['fit'])
        self.assertIn(result['quality'], ('within_initial_screen', 'approximation_review'))
        self.assertEqual(result, module.reduce_opaque(sources))

    def test_source_proven_massless_is_not_given_invented_mass(self):
        result = self.implementation().reduce_opaque([
            {'weight': 1, 'layers': [{'R': 2, 'C': 0}]}])
        self.assertEqual(result['layers'], [{'R': 2., 'C': 0., 'model': 'Material:NoMass'}])

    def test_unknown_or_invalid_operands_are_never_normalized_away(self):
        module = self.implementation()
        for bad in (None, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                module.reduce_opaque([{'weight': 1, 'layers': [{'R': bad, 'C': 2}]}])
        with self.assertRaises(ValueError):
            module.reduce_opaque([{'weight': .4, 'layers': [{'R': 1, 'C': 2}]}])


if __name__ == '__main__':
    unittest.main()
