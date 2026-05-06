from __future__ import annotations

from typing import Any

import reflex as rx
from reflex import event
from reflex.components.core.upload import Upload
from reflex.state import State


class UploadCreateDefUseState(State):
    @event
    def handle_upload(self, files: Any):
        pass


class TestComponentsUploadCreateDefUsePairsQA:
    def test_components_upload_create_def_use_pairs_case(self):
        Upload.is_used = False

        upload = Upload.create(
            rx.text("Drop reports"),
            id="qa_upload",
            class_name="surface",
            on_drop=UploadCreateDefUseState.handle_upload,
            border="1px solid var(--gray-6)",
            padding="2",
        )

        assert isinstance(upload, Upload)
        assert Upload.is_used
        assert len(upload.children) == 1
        assert len(upload.children[0].children) == 2
        assert str(upload.children[0].children[1].children[0].contents) == '"Drop reports"'
