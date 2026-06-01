from __future__ import annotations

import numpy as np

import control as ct


def _ss_siso(name, gain=1.0, pole=-1.0, inputs="u", outputs="y"):
    return ct.ss(
        [[pole]], [[gain]], [[1.0]], [[0.0]],
        name=name, inputs=inputs, outputs=outputs)


def _static(name, matrix, inputs, outputs):
    matrix = np.asarray(matrix, dtype=float)
    return ct.ss([], [], [], matrix, name=name, inputs=inputs, outputs=outputs)


class TestInterconnectExplicitFeedbackQA:
    def test_explicit_feedback_loop(self):
        plant = _ss_siso("P", gain=2.0, pole=-2.0, inputs="u", outputs="y")
        controller = _ss_siso("C", gain=3.0, pole=-3.0, inputs="e", outputs="u")
        closed = ct.interconnect(
            [controller, plant],
            connections=[["P.u", "C.u"], ["C.e", "-P.y"]],
            inplist=["C.e"],
            outlist=["P.y"],
            name="closed_explicit",
        )

        assert closed.ninputs == 1
        assert closed.noutputs == 1
        assert closed.nstates == 2


class TestInterconnectImplicitWithSummingQA:
    def test_implicit_named_signals(self):
        plant = _ss_siso("P", gain=1.5, pole=-1.2, inputs="u", outputs="y")
        controller = _ss_siso("C", gain=2.0, pole=-2.5, inputs="e", outputs="u")
        summer = ct.summing_junction(inputs=["r", "-y"], output="e", name="sum")
        closed = ct.interconnect(
            [controller, plant, summer],
            inplist="r",
            outlist="y",
            name="closed_implicit",
        )

        assert closed.ninputs == 1
        assert closed.noutputs == 1
        assert closed.nstates == 2


class TestInterconnectVectorSignalsQA:
    def test_vector_signal_slices(self):
        plant = ct.ss(
            np.diag([-1.0, -2.0]),
            np.eye(2),
            np.eye(2),
            np.zeros((2, 2)),
            name="P",
            inputs=["u[0]", "u[1]"],
            outputs=["y[0]", "y[1]"],
        )
        controller = _static(
            "K",
            [[2.0, 0.25], [-0.5, 1.5]],
            inputs=["e[0]", "e[1]"],
            outputs=["u[0]", "u[1]"],
        )
        summer = ct.summing_junction(
            inputs=["r", "-y"], output="e", dimension=2, name="sum")
        closed = ct.interconnect(
            [controller, plant, summer],
            connections=[
                ["P.u[:]", "K.u[:]"],
                ["K.e", "sum.e"],
                ["sum.y", "-P.y"],
            ],
            inplist="sum.r",
            outlist="P.y[:]",
            name="closed_vector",
        )

        assert closed.ninputs == 2
        assert closed.noutputs == 2
        assert closed.nstates == 2


class TestInterconnectTupleSpecsQA:
    def test_tuple_specs_and_gains(self):
        left = _ss_siso("left", gain=1.0, pole=-0.7, inputs="u", outputs="v")
        right = _ss_siso("right", gain=1.0, pole=-1.7, inputs="v", outputs="y")
        closed = ct.interconnect(
            [left, right],
            connections=[[(1, 0), (0, 0, -2.0)]],
            inplist=[(0, 0)],
            outlist=[(1, 0, 0.5), (0, 0, -0.25)],
            name="tuple_specs",
        )

        assert closed.ninputs == 1
        assert closed.noutputs == 2
        assert closed.nstates == 2


class TestInterconnectInputAsOutputQA:
    def test_outlist_can_reference_subsystem_input(self):
        plant = _ss_siso("P", gain=1.0, pole=-4.0, inputs="u", outputs="y")
        passthrough = _static("D", [[1.0]], inputs=["r"], outputs=["u"])
        closed = ct.interconnect(
            [passthrough, plant],
            connections=[["P.u", "D.u"]],
            inplist="D.r",
            outlist=["P.y", "P.u"],
            name="input_echo",
        )

        assert closed.ninputs == 1
        assert closed.noutputs == 2
        assert closed.nstates == 1


class TestInterconnectConnectionsFalseQA:
    def test_connections_false_keeps_empty_connect_map(self):
        first = _ss_siso("A", gain=1.0, pole=-1.0, inputs="u", outputs="y")
        second = _ss_siso("B", gain=1.0, pole=-2.0, inputs="v", outputs="z")
        disconnected = ct.interconnect(
            [first, second],
            connections=False,
            inplist=["A.u", "B.v"],
            outlist=["A.y", "B.z"],
            check_unused=False,
            name="disconnected",
        )

        assert disconnected.ninputs == 2
        assert disconnected.noutputs == 2
        assert np.count_nonzero(disconnected.connect_map) == 0


class TestInterconnectAddUnusedQA:
    def test_add_unused_promotes_open_signals(self):
        used = _ss_siso("used", gain=1.0, pole=-1.0, inputs="u", outputs="y")
        loose = _ss_siso("loose", gain=1.0, pole=-3.0, inputs="v", outputs="z")
        sys = ct.interconnect(
            [used, loose],
            connections=[["used.u", "loose.z"]],
            inplist=["loose.v"],
            outlist=["used.y"],
            add_unused=True,
            check_unused=True,
            name="add_unused_case",
        )

        assert sys.ninputs >= 1
        assert sys.noutputs >= 1
        assert sys.nstates == 2


class TestInterconnectDuplicateSystemQA:
    def test_duplicate_object_is_copied(self):
        block = _ss_siso("block", gain=1.0, pole=-1.0, inputs="u", outputs="y")
        sys = ct.interconnect(
            [block, block],
            connections=False,
            inplist=[(0, 0), (1, 0)],
            outlist=[(0, 0), (1, 0)],
            check_unused=False,
            warn_duplicate=False,
            name="duplicate_case",
        )

        assert len(sys.syslist) == 2
        assert sys.ninputs == 2
        assert sys.noutputs == 2


class TestInterconnectNonlinearQA:
    def test_nonlinear_interconnected_system(self):
        def update(t, x, u, params):
            return [-params["decay"] * x[0] + np.tanh(u[0])]

        def output(t, x, u, params):
            return [x[0] + params["bias"]]

        dyn = ct.nlsys(
            update, output, states=["x"], inputs=["u"], outputs=["y"],
            params={"decay": 1.25, "bias": 0.2}, name="dyn")
        summer = ct.summing_junction(inputs=["r", "-y"], output="u", name="sum")
        sys = ct.interconnect(
            [dyn, summer],
            inplist="r",
            outlist="y",
            params={"decay": 1.25, "bias": 0.2},
            name="nonlinear_case",
        )

        assert sys.ninputs == 1
        assert sys.noutputs == 1
        assert sys.nstates == 1


class TestInterconnectTransferFunctionConversionQA:
    def test_transfer_function_subsystems_are_converted(self):
        plant = ct.tf([1.0], [1.0, 2.0], inputs="u", outputs="y", name="P")
        controller = ct.tf([2.0, 1.0], [1.0, 3.0], inputs="e", outputs="u", name="C")
        summer = ct.summing_junction(inputs=["r", "-y"], output="e", name="sum")
        closed = ct.interconnect(
            [controller, plant, summer],
            inplist="r",
            outlist="y",
            name="tf_conversion_case",
        )

        assert closed.ninputs == 1
        assert closed.noutputs == 1
        assert closed.nstates == 2
