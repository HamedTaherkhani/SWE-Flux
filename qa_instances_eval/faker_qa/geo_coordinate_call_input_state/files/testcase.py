from faker import Faker


class TestGeoCoordinateCallInputStateQA:
    def test_geo_coordinate_call_input_state_case(self):
        """
        Burns RNG via `location_on_land` / `local_latlng` (list filtering + random_element)
        without entering `coordinate`, then mixes explicit `coordinate(center=..., radius=...)`
        with `latlng()` which only calls `coordinate` with defaults.
        """
        fake = Faker()
        fake.seed_instance(999001)
        fake.longitude()
        fake.location_on_land()
        fake.local_latlng("DE")
        fake.local_latlng("FR", coords_only=True)
        fake.coordinate(center=-12.375, radius=0.75)
        fake.latlng()


if __name__ == "__main__":
    t = TestGeoCoordinateCallInputStateQA()
    t.test_geo_coordinate_call_input_state_case()
