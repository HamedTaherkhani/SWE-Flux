from keras.src import testing
from keras.src.distribution.distribution_lib import DeviceMesh
from keras.src.distribution.distribution_lib import LayoutMap


class DistributionLayoutMapStateQATest(testing.TestCase):
    def test_layoutmap_matching_keys_state_on_ambiguous_regex(self):
        device_mesh = DeviceMesh(
            shape=(2,),
            axis_names=("batch",),
            devices=["cpu:0", "cpu:1"],
        )
        layout_map = LayoutMap(device_mesh)

        # Intentionally create two overlapping regex entries.
        layout_map["dense.*kernel"] = (None, "batch")
        layout_map[".*dense_1.*"] = ("batch", None)

        # Query path is designed to match both regex keys.
        with self.assertRaisesRegex(ValueError, "matches multiple layout"):
            _ = layout_map["encoder/dense_1/kernel"]
