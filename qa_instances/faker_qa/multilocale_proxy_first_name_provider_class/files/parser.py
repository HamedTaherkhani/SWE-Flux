#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Bound method call: self repr includes the concrete Provider class.
_SELF_CLASS_RE = re.compile(
    r"'self': '<(faker\.providers\.person\.[a-zA-Z0-9_]+\.Provider) object at 0x[0-9a-f]+>'"
)
# Fallback: file path under faker/providers/person/<LOCALE>/__init__.py
_PATH_LOCALE_RE = re.compile(
    r"faker/providers/person/([a-zA-Z0-9_]+)/__init__\.py:\d+ .* event=call "
)


def extract_output(trace_text: str) -> dict[str, str]:
    for line in trace_text.splitlines():
        if " event=call " not in line:
            continue
        if "/faker/providers/person/" not in line.replace("\\", "/"):
            continue
        if "first_name" not in line:
            continue
        # The user-facing `first_name()` call; skip imports of name helpers if any.
        if ".first_name_pair" in line or ".first_name_male" in line or ".first_name_female" in line:
            continue

        m = _SELF_CLASS_RE.search(line)
        if m:
            return {"concrete_person_provider_class": m.group(1)}

        pm = _PATH_LOCALE_RE.search(line.replace("\\", "/"))
        if pm:
            loc = pm.group(1)
            return {"concrete_person_provider_class": f"faker.providers.person.{loc}.Provider"}

    raise ValueError(
        "Could not find a Person provider `first_name` call event with a concrete class in the trace.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/multilocale_proxy_first_name_provider_class/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/multilocale_proxy_first_name_provider_class/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(1337)\n"
        "fake = Faker(['en_US', 'de_DE', 'ja_JP', 'fr_FR'])\n"
        "fake.first_name()\n"
    )

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `faker_qa/multilocale_proxy_first_name_provider_class/files/testcase.py`, class "
            "`TestMultilocaleProxyFirstNameProviderClassQA`, method "
            "`test_multilocale_proxy_first_name_provider_class_case`. The test seeds the shared "
            "Faker RNG with `Faker.seed(1337)`, constructs a four-locale proxy "
            "`Faker(['en_US', 'de_DE', 'ja_JP', 'fr_FR'])`, then calls `fake.first_name()`. "
            "That call is resolved through `faker/proxy.py` (`Faker.__getattr__` → `_select_factory` "
            "→ `_map_provider_method` → `_select_factory_choice`, which uses `random.choice` over "
            "compatible `Generator` instances). At runtime this selects exactly one locale-specific "
            "Person provider whose `first_name` implementation runs (dynamic dispatch across localized "
            "Provider subclasses). "
            "What is the fully qualified name of that **Person Provider class** "
            "(the `Provider` subclass in `faker.providers.person.<LOCALE>` whose `first_name` method "
            "is actually invoked — format `faker.providers.person.<LOCALE>.Provider`)?"
        ),
        "template_answer": {"concrete_person_provider_class": "str"},
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
