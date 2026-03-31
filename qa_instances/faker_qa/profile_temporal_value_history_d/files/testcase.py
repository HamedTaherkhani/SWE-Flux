from faker import Faker

class TestProfileTemporalValueHistoryDQA:
    def test_profile_temporal_value_history_d_case(self):
        fake = Faker()
        Faker.seed(42)
        
        profile = fake.profile(fields=["ssn", "name"])
        
        assert "ssn" in profile
        assert "name" in profile
        assert len(profile) == 2
