from __future__ import annotations

from reflex.route import get_route_args


class TestRouteGetRouteArgsInvariantOneQA:
    def test_single_slug(self):
        assert get_route_args("/blog/[slug]") == {"slug": "arg_single"}


class TestRouteGetRouteArgsInvariantTwoQA:
    def test_two_long_args(self):
        assert get_route_args("/shop/[category]/[product]") == {
            "category": "arg_single",
            "product": "arg_single",
        }


class TestRouteGetRouteArgsInvariantThreeQA:
    def test_short_second_arg(self):
        assert get_route_args("/a/[longname]/[x]") == {
            "longname": "arg_single",
            "x": "arg_single",
        }


class TestRouteGetRouteArgsInvariantFourQA:
    def test_catchall_after_single(self):
        assert get_route_args("/docs/[section]/[...rest]") == {
            "section": "arg_single",
            "rest": "arg_list",
        }


class TestRouteGetRouteArgsInvariantFiveQA:
    def test_optional_catchall(self):
        assert get_route_args("/files/[[...path]]") == {"path": "arg_list"}


class TestRouteGetRouteArgsInvariantSixQA:
    def test_three_single_args(self):
        assert get_route_args("/u/[org]/[team]/[member]") == {
            "org": "arg_single",
            "team": "arg_single",
            "member": "arg_single",
        }


class TestRouteGetRouteArgsInvariantSevenQA:
    def test_short_arg_after_two(self):
        assert get_route_args("/r/[first]/[second]/[q]") == {
            "first": "arg_single",
            "second": "arg_single",
            "q": "arg_single",
        }


class TestRouteGetRouteArgsInvariantEightQA:
    def test_plain_prefix_and_arg(self):
        assert get_route_args("/settings/profile/[tab]") == {"tab": "arg_single"}


class TestRouteGetRouteArgsInvariantNineQA:
    def test_nested_catchall_name(self):
        assert get_route_args("/assets/[bucket]/[...key]") == {
            "bucket": "arg_single",
            "key": "arg_list",
        }


class TestRouteGetRouteArgsInvariantTenQA:
    def test_four_single_args(self):
        assert get_route_args("/m/[aa]/[bbb]/[c]/[dddd]") == {
            "aa": "arg_single",
            "bbb": "arg_single",
            "c": "arg_single",
            "dddd": "arg_single",
        }
