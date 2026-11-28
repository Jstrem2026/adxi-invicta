"""Tests for the exact geometry (atlaslib/geometry.py). Run from the repo root:
    python -m unittest discover -s Invicta/tests -t Invicta
"""
import math
import unittest

from atlaslib import geometry as G

SQ = [(0, 0), (2, 0), (2, 2), (0, 2)]


class Areas(unittest.TestCase):
    def test_polygon_area(self):
        self.assertAlmostEqual(G.polygon_area(SQ), 4.0)
        self.assertAlmostEqual(G.polygon_area(list(reversed(SQ))), 4.0)

    def test_circle_overlap_quarter(self):
        # a unit circle centred on the square's corner: a quarter of it is inside
        self.assertAlmostEqual(G.circle_overlap_area(SQ, 0, 0, 1), math.pi / 4, places=5)

    def test_circle_overlap_whole_and_none(self):
        self.assertAlmostEqual(G.circle_overlap_area(SQ, 1, 1, 0.5), math.pi * 0.25, places=5)
        self.assertEqual(G.circle_overlap_area(SQ, 10, 10, 1), 0.0)

    def test_circle_crossing_an_edge_with_no_corner_inside(self):
        # The old corner test missed this case: an edge cuts the circle, no corner is in it.
        r, d = 0.5, 0.25  # circle centre 0.25 below the bottom edge
        seg = r * r * math.acos(d / r) - d * math.sqrt(r * r - d * d)
        self.assertAlmostEqual(G.circle_overlap_area(SQ, 1, -d, r), seg, places=5)
        self.assertTrue(G.box_shape([0, 2, 0, 2]).intersects(G.circle(1, -d, r)))

    def test_overlap_area(self):
        self.assertAlmostEqual(G.overlap_area(SQ, [(1, 1), (3, 1), (3, 3), (1, 3)]), 1.0)
        self.assertAlmostEqual(G.overlap_area(SQ, [(2, 0), (3, 0), (3, 2), (2, 2)]), 0.0)


class Shapes(unittest.TestCase):
    def test_building_with_courtyard(self):
        b = {"rect_km": [0, 4, 0, 4], "outline_km": [[[0, 0], [4, 0], [4, 4], [0, 4]]],
             "holes_km": [[[1, 1], [3, 1], [3, 3], [1, 3]]]}
        self.assertAlmostEqual(G.building_shape(b).area, 16 - 4)

    def test_building_bays(self):
        b = {"rect_km": [0, 10, 0, 1], "bays_km": [[0, 1, 0, 1], [5, 6, 0, 1]]}
        self.assertAlmostEqual(G.building_shape(b).area, 2.0)

    def test_self_crossing_ring_is_repaired_not_dropped(self):
        bow = [(0, 0), (2, 2), (2, 0), (0, 2)]  # a figure-of-eight
        g = G.shape(bow)
        self.assertTrue(g.is_valid)
        self.assertAlmostEqual(g.area, 2.0)

    def test_clip_convex_and_concave_windows(self):
        self.assertAlmostEqual(G.polygon_area(G.clip(SQ, [(1, -1), (3, -1), (3, 3), (1, 3)])), 2.0)
        L = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]  # concave window
        self.assertFalse(G.is_convex(L))
        self.assertAlmostEqual(G.polygon_area(G.clip(SQ, L)), 3.0)

    def test_point_in_poly(self):
        self.assertTrue(G.point_in_poly(1, 1, SQ))
        self.assertFalse(G.point_in_poly(3, 1, SQ))


class Units(unittest.TestCase):
    def test_us_first(self):
        self.assertEqual(G.fmt_len_m(10), "33 ft (10 m)")
        self.assertEqual(G.fmt_area_m2(60), "646 sq ft (60 m²)")


if __name__ == "__main__":
    unittest.main()
