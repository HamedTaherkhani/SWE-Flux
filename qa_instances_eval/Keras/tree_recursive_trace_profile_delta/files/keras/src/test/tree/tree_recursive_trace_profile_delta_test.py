from keras.src import testing
from keras.src.tree import dmtree_impl


class TreeRecursiveTraceProfileDeltaQATest(testing.TestCase):
    def test_single_recursive_walk_signature(self):
        structure = {
            "branch_b": [{"u": (1, 2), "v": [3, 4]}, ("leaf", {"z": 5})],
            "branch_a": ({"k2": 7, "k1": [8, 9]}, {"m": 10, "n": (11, 12)}),
            "branch_c": [{"p": 13}, {"q": [14, 15, {"r": 16}]}],
        }

        flattened = dmtree_impl.flatten_with_path(structure)

        self.assertEqual(len(flattened), 16)
        self.assertEqual(flattened[0][0], ("branch_a", 0, "k1", 0))
        self.assertEqual(flattened[-1][0], ("branch_c", 1, "q", 2, "r"))
