import numpy as np

from control.statesp import drss, rss


class TestRSSPoleLoopSmallContinuousQA:
    def test_seeded_three_state_continuous_siso(self):
        np.random.seed(101)
        sys = rss(states=3, outputs=1, inputs=1, name="qa_rss_101")
        assert sys.nstates == 3
        assert sys.ninputs == 1
        assert sys.noutputs == 1
        assert sys.isctime()


class TestRSSPoleLoopMediumContinuousQA:
    def test_seeded_six_state_continuous_mimo(self):
        np.random.seed(202)
        sys = rss(states=6, outputs=2, inputs=3, name="qa_rss_202")
        assert sys.nstates == 6
        assert sys.ninputs == 3
        assert sys.noutputs == 2
        assert sys.isctime()


class TestRSSPoleLoopStrictlyProperQA:
    def test_seeded_five_state_strictly_proper(self):
        np.random.seed(303)
        sys = rss(
            states=5, outputs=2, inputs=2,
            strictly_proper=True, name="qa_rss_303",
        )
        assert sys.nstates == 5
        assert np.allclose(sys.D, 0)


class TestRSSPoleLoopNamedSignalsQA:
    def test_seeded_named_signal_dimensions(self):
        np.random.seed(404)
        sys = rss(
            states=["xa", "xb", "xc", "xd"],
            inputs=["u0", "u1"],
            outputs=["y0"],
            name="qa_rss_404",
        )
        assert sys.nstates == 4
        assert sys.input_labels == ["u0", "u1"]
        assert sys.output_labels == ["y0"]


class TestRSSPoleLoopLargeContinuousQA:
    def test_seeded_nine_state_continuous(self):
        np.random.seed(505)
        sys = rss(states=9, outputs=3, inputs=2, name="qa_rss_505")
        assert sys.nstates == 9
        assert sys.ninputs == 2
        assert sys.noutputs == 3


class TestDRSSPoleLoopSmallDiscreteQA:
    def test_seeded_four_state_discrete_default_dt(self):
        np.random.seed(606)
        sys = drss(states=4, outputs=1, inputs=2, name="qa_drss_606")
        assert sys.nstates == 4
        assert sys.dt is True
        assert sys.isdtime()


class TestDRSSPoleLoopExplicitDtQA:
    def test_seeded_seven_state_discrete_explicit_dt(self):
        np.random.seed(707)
        sys = drss(states=7, outputs=2, inputs=1, dt=0.25, name="qa_drss_707")
        assert sys.nstates == 7
        assert sys.dt == 0.25


class TestDRSSPoleLoopStrictlyProperQA:
    def test_seeded_eight_state_discrete_strictly_proper(self):
        np.random.seed(808)
        sys = drss(
            states=8, outputs=2, inputs=2,
            strictly_proper=True, name="qa_drss_808",
        )
        assert sys.nstates == 8
        assert np.allclose(sys.D, 0)


class TestDRSSPoleLoopNamedSignalsQA:
    def test_seeded_named_discrete_dimensions(self):
        np.random.seed(909)
        sys = drss(
            states=["x0", "x1", "x2", "x3", "x4", "x5"],
            inputs=["u0"],
            outputs=["y0", "y1", "y2"],
            dt=0.5,
            name="qa_drss_909",
        )
        assert sys.nstates == 6
        assert sys.noutputs == 3
        assert sys.dt == 0.5


class TestRSSPoleLoopTenStateContinuousQA:
    def test_seeded_ten_state_continuous_mimo(self):
        np.random.seed(1001)
        sys = rss(states=10, outputs=2, inputs=4, name="qa_rss_1001")
        assert sys.nstates == 10
        assert sys.ninputs == 4
        assert sys.noutputs == 2
