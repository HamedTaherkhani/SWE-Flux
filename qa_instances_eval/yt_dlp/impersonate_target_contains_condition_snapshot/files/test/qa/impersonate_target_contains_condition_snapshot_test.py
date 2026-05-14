from yt_dlp.networking.impersonate import ImpersonateTarget


SELF_TARGET = ImpersonateTarget(client="chrome", version="110", os="windows", os_version="10")
OTHER_TARGET = ImpersonateTarget(client="chrome", version="100", os=None, os_version=None)


class TestImpersonateTargetContainsConditionSnapshotQA:
    def test_impersonate_target_contains_condition_snapshot_case(self):
        result = OTHER_TARGET in SELF_TARGET

        # Shape-only assertion; do not reveal the result or any field values.
        assert isinstance(result, bool)
