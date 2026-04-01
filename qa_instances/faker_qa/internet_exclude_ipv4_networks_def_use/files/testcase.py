import pytest
from ipaddress import IPv4Network
from faker import Faker

class TestInternetExcludeIpv4NetworksDefUseQA:
    def test_exclude_ipv4_networks_def_use_case(self):
        # Deterministic seed and en_US locale
        fake = Faker('en_US')
        fake.seed_instance(42)
        
        # Define a set of networks to filter
        networks = [
            IPv4Network("192.168.0.0/16"),
            IPv4Network("10.0.0.0/8")
        ]
        
        # Define networks to exclude (overlapping with above)
        networks_to_exclude = [
            IPv4Network("192.168.1.0/24"),
            IPv4Network("10.1.0.0/16")
        ]
        
        from faker.providers.internet import Provider as InternetProvider
        provider = InternetProvider(fake)
        
        # Directly invoke the private-ish method _exclude_ipv4_networks
        res = provider._exclude_ipv4_networks(networks, networks_to_exclude)
        
        # Basic assertions
        assert len(res) > 0
        assert all(isinstance(n, IPv4Network) for n in res)
