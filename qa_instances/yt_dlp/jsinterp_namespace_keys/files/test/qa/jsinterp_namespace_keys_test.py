from yt_dlp.jsinterp import JSInterpreter


class TestJSInterpNamespaceKeysQA:
    def test_jsinterp_namespace_keys_case(self) -> None:
        JSInterpreter._JSInterpreter__named_object_counter = 0
        interp = JSInterpreter(code="")

        namespace = {"seed": 1}
        created_name = interp._named_object(namespace, {"value": 9})

        assert isinstance(created_name, str)
        assert created_name in namespace
