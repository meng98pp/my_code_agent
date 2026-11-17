"""L0：空包可被 Python 找到。"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class L0ImportTests(unittest.TestCase):
    def test_domain_packages_import(self) -> None:
        import agent
        import config
        import core
        import interfaces
        import memory
        import tool

        self.assertTrue(hasattr(agent, "__doc__"))
        self.assertTrue(hasattr(tool, "__doc__"))
        self.assertTrue(hasattr(memory, "__doc__"))
        self.assertTrue(hasattr(core, "__doc__"))
        self.assertTrue(hasattr(config, "__doc__"))
        self.assertTrue(hasattr(interfaces, "__doc__"))

    def test_gitignore_keeps_data_dir_private(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".data/", text)

    def test_readme_documents_memory_root(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("CODE_AGENT_HOME", text)
        self.assertIn("CODE_AGENT_MEMORY_ROOT", text)


if __name__ == "__main__":
    unittest.main()
