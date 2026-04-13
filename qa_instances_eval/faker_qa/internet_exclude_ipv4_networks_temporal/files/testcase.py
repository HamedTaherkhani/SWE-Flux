import pytest
from faker import Faker

class TestInternetExcludeIpv4NetworksQA:

    def test_internet_exclude_ipv4_networks_case(self):
        faker = Faker()
        faker.seed_instance(42)
        
        # Calling ipv4_public directly invokes _get_public_networks_and_weights
        # which subsequently triggers _exclude_ipv4_networks
        _ = faker.ipv4_public(network=False, address_class="a")
