from faker import Faker


class TestMiscPasswordRandomIndexWhileLoopIterationsQA:
    def test_misc_password_random_index_while_loop_iterations_case(self):
        """Drive `Provider.password` with all character classes so the unique-index
        sampling loop must run until four distinct positions exist (with possible
        duplicate draws). Seeded for deterministic oracle extraction.
        """
        fake = Faker()
        fake.seed_instance(777888999)
        pwd = fake.password(
            length=8,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )
        assert isinstance(pwd, str)
        assert len(pwd) == 8
