from pathlib import Path

from yt_dlp.globals import plugin_dirs
from yt_dlp.plugins import PluginFinder


class TestPluginCandidateInputStateIndirectQA:
    def test_plugin_candidate_input_state_indirect_case(self) -> None:
        root = Path("/tmp/ytdlp_qa_candidate_dir_state")
        (root / "yt_dlp_plugins" / "extractor").mkdir(parents=True, exist_ok=True)

        old_dirs = plugin_dirs.value
        plugin_dirs.value = [str(root)]
        try:
            finder = PluginFinder("extractor")
            out = list(finder.search_locations("yt_dlp_plugins.extractor"))
            assert isinstance(out, list)
        finally:
            plugin_dirs.value = old_dirs
