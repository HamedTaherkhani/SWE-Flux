from yt_dlp.jsinterp import JSInterpreter


JS_SOURCE = '''function compute(alpha, beta, gamma) {
    var s = function(p) { return p + p; };
    var t = function(q) { return q * q; };
    var u = function(r) { return r - 1; };
    return s(alpha) + t(beta) - u(gamma);
}'''


def _collect_first_interpret_args(jsi):
    captured = {}
    original = JSInterpreter.interpret_statement

    def spy(self, stmt, local_vars, allow_recursion=100):
        if not captured:
            captured["stmt"] = stmt
            captured["local_vars_keys"] = sorted(local_vars)
            captured["argname_bindings"] = {
                k: local_vars[k]
                for k in sorted(local_vars)
                if not k.startswith("__yt_dlp_jsinterp_obj")
            }
            captured["allow_recursion"] = allow_recursion
        return original(self, stmt, local_vars, allow_recursion)

    JSInterpreter.interpret_statement = spy
    try:
        jsi.call_function("compute", 4, 5, 6)
    finally:
        JSInterpreter.interpret_statement = original
    return captured


class TestJsInterpreterFirstStatementInputsQA:
    def test_jsinterpreter_first_statement_inputs_case(self):
        jsi = JSInterpreter(JS_SOURCE)
        snapshot = _collect_first_interpret_args(jsi)

        # Shape-only assertions; do not reveal the captured values.
        assert isinstance(snapshot, dict)
        assert {"stmt", "local_vars_keys", "argname_bindings",
                "allow_recursion"} <= set(snapshot)
        assert isinstance(snapshot["stmt"], str)
        assert isinstance(snapshot["local_vars_keys"], list)
        assert isinstance(snapshot["argname_bindings"], dict)
        assert isinstance(snapshot["allow_recursion"], int)
