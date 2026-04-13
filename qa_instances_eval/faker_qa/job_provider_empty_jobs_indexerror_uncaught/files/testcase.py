import pytest
from faker import Faker


class TestJobProviderEmptyJobsIndexErrorUncaughtQA:
    def test_job_provider_empty_jobs_indexerror_uncaught_case(self):
        """
        Exercise normal job/job_male/job_female dispatch, then clear the provider's
        `jobs` sequence so `Provider.job` -> `random_element` yields an empty sample
        and indexing fails at `faker/providers/job/__init__.py` line 650.
        """
        fake = Faker()
        fake.seed_instance(2207)
        fake.job()
        fake.job_male()
        fake.job_female()
        job_provider = fake.provider("faker.providers.job")
        assert job_provider is not None
        job_provider.jobs = ()
        with pytest.raises(IndexError) as exc_info:
            fake.job()
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestJobProviderEmptyJobsIndexErrorUncaughtQA()
    t.test_job_provider_empty_jobs_indexerror_uncaught_case()
