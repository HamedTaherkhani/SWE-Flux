import collections

from keras.src import testing
from keras.src.tree import dmtree_impl


class TreeFlattenWithPathLoopKeyOrderInvariantHardQATest(testing.TestCase):
    def _run_case(self, structure):
        flat_with_path = dmtree_impl.flatten_with_path(structure)
        flat = dmtree_impl.flatten(structure)
        self.assertEqual(len(flat_with_path), len(flat))
        self.assertListEqual([value for _, value in flat_with_path], flat)

    def test_case_01(self):
        structure = collections.OrderedDict(
            [
                ("zeta", {"k2": 2, "k1": 1}),
                ("alpha", [3, 4]),
                ("mu", (5, 6)),
            ]
        )
        self._run_case(structure)

    def test_case_02(self):
        structure = {
            "root_b": collections.OrderedDict(
                [("q", [1, 2]), ("a", {"x": 0}), ("m", (1,))]
            ),
            "root_a": {"delta": 7, "beta": 8},
        }
        self._run_case(structure)

    def test_case_03(self):
        structure = [
            collections.OrderedDict(
                [("node3", {"b": 1, "a": 2}), ("node1", (3, 4)), ("node2", [5])]
            ),
            {"k3": collections.OrderedDict([("x2", 9), ("x1", 10)])},
        ]
        self._run_case(structure)

    def test_case_04(self):
        structure = collections.OrderedDict(
            [
                (
                    "layer2",
                    collections.OrderedDict(
                        [("w", [1]), ("a", [2]), ("m", [3])]
                    ),
                ),
                ("layer1", {"c": 1, "a": 2, "b": 3}),
            ]
        )
        self._run_case(structure)

    def test_case_05(self):
        structure = {
            "top": (
                collections.OrderedDict(
                    [("gamma", {"t": 1}), ("beta", {"s": 2}), ("delta", {"r": 3})]
                ),
                [collections.OrderedDict([("p", 1), ("o", 2)])],
            ),
            "aux": {"u": 9, "v": 10},
        }
        self._run_case(structure)

    def test_case_06(self):
        structure = collections.OrderedDict(
            [
                (
                    "outer",
                    [
                        {"d": 4, "b": 2, "c": 3},
                        collections.OrderedDict(
                            [("k9", 9), ("k1", 1), ("k5", 5)]
                        ),
                    ],
                ),
                ("inner", {"left": (1, 2), "right": (3, 4)}),
            ]
        )
        self._run_case(structure)

    def test_case_07(self):
        structure = {
            "mix": collections.OrderedDict(
                [
                    ("zz", {"b2": [1, 2], "a1": [3]}),
                    ("aa", {"z9": (4,), "x8": (5,)}),
                    ("mm", {"m1": {"q": 7, "p": 6}}),
                ]
            ),
            "list": [collections.OrderedDict([("r", 1), ("a", 2), ("n", 3)])],
        }
        self._run_case(structure)

    def test_case_08(self):
        structure = (
            collections.OrderedDict(
                [("high", [1]), ("low", [2]), ("mid", [3]), ("alpha", [4])]
            ),
            {
                "sub": collections.OrderedDict(
                    [("three", 3), ("one", 1), ("two", 2)]
                ),
                "plain": {"y": 2, "x": 1},
            },
        )
        self._run_case(structure)

    def test_case_09(self):
        structure = collections.OrderedDict(
            [
                (
                    "branch",
                    {
                        "kappa": collections.OrderedDict(
                            [("v3", 3), ("v1", 1), ("v2", 2)]
                        ),
                        "alpha": [0, 1, 2],
                    },
                ),
                ("tail", {"z": 26, "a": 1}),
            ]
        )
        self._run_case(structure)

    def test_case_10(self):
        structure = {
            "ordered": collections.OrderedDict(
                [
                    ("m", {"d": 4, "a": 1}),
                    ("b", {"g": 7, "c": 3}),
                    ("x", {"k": 11, "h": 8}),
                ]
            ),
            "nested": (
                {"j": 10, "f": 6},
                collections.OrderedDict([("t", [1, 2]), ("e", [3, 4])]),
            ),
        }
        self._run_case(structure)

    def test_case_11(self):
        structure = collections.OrderedDict(
            [
                (
                    "bucket",
                    [
                        collections.OrderedDict(
                            [("l3", 3), ("l1", 1), ("l2", 2)]
                        ),
                        {"r3": 3, "r1": 1, "r2": 2},
                    ],
                ),
                (
                    "meta",
                    {
                        "d2": collections.OrderedDict(
                            [("c", 3), ("a", 1), ("b", 2)]
                        ),
                        "d1": {"p": 16, "o": 15},
                    },
                ),
            ]
        )
        self._run_case(structure)

    def test_case_12(self):
        structure = {
            "root": collections.OrderedDict(
                [
                    ("segment9", {"n": [1], "m": [2]}),
                    ("segment2", {"b": [3], "a": [4]}),
                    ("segment5", {"f": [5], "e": [6]}),
                ]
            ),
            "tail": collections.OrderedDict(
                [("zz", (1, 2)), ("yy", (3, 4)), ("xx", (5, 6))]
            ),
        }
        self._run_case(structure)
