#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# The trace plugin emits call events for every method whose `co_name` is
# `decrypt` in `/testbed/yt_dlp/cookies.py`. There are FOUR such methods:
#   - ChromeCookieDecryptor.decrypt        (base, line 412, raises NotImplementedError)
#   - LinuxChromeCookieDecryptor.decrypt   (line 445)
#   - MacChromeCookieDecryptor.decrypt     (line 494)
#   - WindowsChromeCookieDecryptor.decrypt (line 521)
# At the call event we extract `self` from locals; its default repr is
# `<yt_dlp.cookies.ClassName object at 0xADDR>`. Parsing that repr gives the
# concrete class. The line number of the call event is where the method is
# defined (i.e., the `def decrypt(self, encrypted_value):` line).
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/cookies\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.cookies\.decrypt) "
    r"event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

SELF_REPR_RE = re.compile(
    r"<(?:[\w.]+\.)?(?P<cls>\w+) object at 0x[0-9a-fA-F]+>"
)


def extract_dispatch(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No `decrypt` call event captured.")

    # The first call event for `decrypt` corresponds to the dispatched method
    # invoked from the test (via decryptor.decrypt(...)).
    m = matches[0]
    lineno = int(m.group("lineno"))
    locals_blob = m.group("locals")

    # Locals are emitted as a Python dict-literal of strings (key:repr) form.
    # We don't need to literal_eval the whole thing; just pull `self`'s repr.
    self_match = re.search(
        r"'self':\s*(?P<q>['\"])(?P<repr>(?:\\.|(?!(?P=q)).)*)(?P=q)",
        locals_blob,
    )
    if not self_match:
        raise ValueError(
            f"`self` not found in decrypt call locals: {locals_blob!r}")
    self_repr = self_match.group("repr")
    cls_match = SELF_REPR_RE.search(self_repr)
    if not cls_match:
        raise ValueError(
            f"Could not parse class from self repr: {self_repr!r}")

    return {
        "dispatched_class_name": cls_match.group("cls"),
        "dispatched_method_def_line": lineno,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/chrome_cookie_decryptor_decrypt_dispatch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/chrome_cookie_decryptor_decrypt_dispatch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_dispatch(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/chrome_cookie_decryptor_decrypt_dispatch_test.py`, class "
            "`TestChromeCookieDecryptorDecryptDispatchQA`, method "
            "`test_chrome_cookie_decryptor_decrypt_dispatch_case`. The test invokes the "
            "factory `yt_dlp.cookies.get_cookie_decryptor` (defined at line 416 in "
            "`yt_dlp/cookies.py`) and then calls `decryptor.decrypt(...)` inside a "
            "`with contextlib.suppress(Exception):` block. The relevant "
            "`yt_dlp/cookies.py` definitions are:\n"
            "```\n"
            "382: class ChromeCookieDecryptor:\n"
            "    ...\n"
            "412:     def decrypt(self, encrypted_value):\n"
            "413:         raise NotImplementedError('Must be implemented by sub classes')\n"
            "\n"
            "416: def get_cookie_decryptor(browser_root, browser_keyring_name, logger, *, keyring=None, meta_version=None):\n"
            "417:     if sys.platform == 'darwin':\n"
            "418:         return MacChromeCookieDecryptor(browser_keyring_name, logger, meta_version=meta_version)\n"
            "419:     elif sys.platform in ('win32', 'cygwin'):\n"
            "420:         return WindowsChromeCookieDecryptor(browser_root, logger, meta_version=meta_version)\n"
            "421:     return LinuxChromeCookieDecryptor(browser_keyring_name, logger, keyring=keyring, meta_version=meta_version)\n"
            "\n"
            "424: class LinuxChromeCookieDecryptor(ChromeCookieDecryptor):\n"
            "    ...\n"
            "445:     def decrypt(self, encrypted_value):\n"
            "        ...\n"
            "\n"
            "480: class MacChromeCookieDecryptor(ChromeCookieDecryptor):\n"
            "    ...\n"
            "494:     def decrypt(self, encrypted_value):\n"
            "        ...\n"
            "\n"
            "514: class WindowsChromeCookieDecryptor(ChromeCookieDecryptor):\n"
            "    ...\n"
            "521:     def decrypt(self, encrypted_value):\n"
            "        ...\n"
            "```\n\n"
            "ENVIRONMENT: the test runs inside a Linux Docker container "
            "(`starryzhang/sweb.eval.x86_64.yt-dlp_1776_yt-dlp-12714:latest`), so at "
            "test execution time `sys.platform == 'linux'` -- it is neither `'darwin'` "
            "nor in `('win32', 'cygwin')`.\n\n"
            "DISPATCH QUESTION: at the line `decryptor.decrypt(b\"v10\" + b\"\\x00\" * "
            "16)` inside the `with contextlib.suppress(Exception):` block of the test "
            "method, Python performs DYNAMIC method dispatch on `decryptor`. Predict "
            "WHICH CONCRETE CLASS'S `decrypt` METHOD is actually executed, and at WHICH "
            "SOURCE LINE that method is defined. Apply Python's standard MRO rules "
            "given the actual runtime type of `decryptor` returned by "
            "`get_cookie_decryptor` for `sys.platform == 'linux'`.\n\n"
            "Return a JSON object with EXACTLY these two keys:\n"
            "- `dispatched_class_name`: str -- the bare class name (no module prefix) "
            "of the concrete class whose `decrypt` method actually executes (one of "
            "`\"ChromeCookieDecryptor\"`, `\"LinuxChromeCookieDecryptor\"`, "
            "`\"MacChromeCookieDecryptor\"`, `\"WindowsChromeCookieDecryptor\"`).\n"
            "- `dispatched_method_def_line`: int -- the line number in "
            "`yt_dlp/cookies.py` where the dispatched method's `def decrypt(self, "
            "encrypted_value):` header appears (412, 445, 494, or 521)."
        ),
        "template_answer": {
            "dispatched_class_name": "str",
            "dispatched_method_def_line": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
