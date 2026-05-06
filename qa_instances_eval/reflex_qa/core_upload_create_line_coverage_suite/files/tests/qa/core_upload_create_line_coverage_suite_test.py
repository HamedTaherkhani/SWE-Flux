from __future__ import annotations

import reflex as rx
from reflex.components.core.upload import StyledUpload, Upload


def assert_upload(component) -> None:
    assert isinstance(component, Upload)
    assert Upload.is_used
    Upload.is_used = False


class TestCoreUploadCreateLineCoverageOneQA:
    def test_default_upload_without_children(self):
        assert_upload(Upload.create())


class TestCoreUploadCreateLineCoverageTwoQA:
    def test_default_upload_with_boolean_flag(self):
        assert_upload(Upload.create(id="avatar", disabled=False))


class TestCoreUploadCreateLineCoverageThreeQA:
    def test_default_upload_with_list_class_name(self):
        assert_upload(Upload.create(id="gallery", class_name=["drop-a", "drop-b"]))


class TestCoreUploadCreateLineCoverageFourQA:
    def test_upload_with_children_and_box_props(self):
        assert_upload(
            Upload.create(
                rx.text("Drop files"),
                rx.button("Browse"),
                id="with-children",
                border="1px solid red",
                padding="2rem",
            )
        )


class TestCoreUploadCreateLineCoverageFiveQA:
    def test_default_upload_with_no_click(self):
        assert_upload(
            Upload.create(
                id="no-click",
                no_click=True,
            )
        )


class TestCoreUploadCreateLineCoverageSixQA:
    def test_default_upload_with_max_files(self):
        assert_upload(
            Upload.create(
                id="max-files",
                max_files=3,
            )
        )


class TestCoreUploadCreateLineCoverageSevenQA:
    def test_default_upload_with_no_keyboard(self):
        assert_upload(
            Upload.create(
                id="keyboard-disabled",
                no_keyboard=True,
            )
        )


class TestCoreUploadCreateLineCoverageEightQA:
    def test_default_upload_with_multiple_supported_props(self):
        assert_upload(
            Upload.create(
                id="supported-props",
                multiple=False,
                accept={"image/png": [".png"]},
                disabled=False,
            )
        )


class TestCoreUploadCreateLineCoverageNineQA:
    def test_styled_upload_delegates_to_upload_create(self):
        component = StyledUpload.create(
            rx.vstack(rx.text("Styled"), rx.text("Upload")),
            id="styled",
        )

        assert isinstance(component, StyledUpload)
        assert Upload.is_used
        Upload.is_used = False


class TestCoreUploadCreateLineCoverageTenQA:
    def test_upload_namespace_root_delegates_to_upload_create(self):
        assert_upload(
            rx.upload.root(
                rx.text("Namespace root"),
                id="namespace-root",
            )
        )
