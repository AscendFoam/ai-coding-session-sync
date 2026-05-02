from __future__ import annotations

import json
import unittest
from pathlib import Path


class WebSmokeTest(unittest.TestCase):
    def test_web_prototype_files_exist(self) -> None:
        web_root = Path(__file__).resolve().parents[1] / "apps" / "web"
        self.assertTrue((web_root / "index.html").exists())
        self.assertTrue((web_root / "styles.css").exists())
        self.assertTrue((web_root / "app.js").exists())
        self.assertTrue((web_root / "package.json").exists())

    def test_web_prototype_exposes_three_pane_workbench_hooks(self) -> None:
        web_root = Path(__file__).resolve().parents[1] / "apps" / "web"
        html = (web_root / "index.html").read_text(encoding="utf-8")
        self.assertIn("Session Library", html)
        self.assertIn("Project View", html)
        self.assertIn("Session Detail", html)
        self.assertIn("Command / Status Strip", html)
        self.assertIn('id="projectSessionList"', html)
        self.assertIn('id="projectContexts"', html)
        self.assertIn('id="connectionSignals"', html)
        self.assertIn('id="rescanButton"', html)
        self.assertIn('id="openApiButton"', html)
        self.assertIn('id="copySessionKeyButton"', html)
        self.assertIn('id="commandPaletteButton"', html)
        self.assertIn('id="activityLog"', html)
        self.assertIn('id="exportHistoryButton"', html)
        self.assertIn('id="historyFilterAll"', html)
        self.assertIn('id="historyFilterWarn"', html)
        self.assertIn('id="historyFilterSync"', html)
        self.assertIn('id="historyFilterDetail"', html)
        self.assertIn('id="historyGroupSource"', html)
        self.assertIn('id="historyGroupCategory"', html)
        self.assertIn('id="historyGroupFlat"', html)
        self.assertIn('id="historySortDesc"', html)
        self.assertIn('id="historySortAsc"', html)
        self.assertIn('id="commandPaletteOverlay"', html)
        self.assertIn('id="commandPaletteMeta"', html)
        self.assertIn('id="commandPaletteList"', html)
        self.assertIn('id="workspaceBanner"', html)
        self.assertIn('id="projectBanner"', html)
        self.assertIn('id="detailBanner"', html)
        self.assertIn('id="detailTabManifest"', html)
        self.assertIn('data-testid="detail-tab-patch"', html)
        self.assertIn('data-testid="detail-tab-compare"', html)
        self.assertIn('data-testid="detail-tab-handoff"', html)
        self.assertIn('data-testid="action-feedback"', html)
        self.assertIn('data-testid="activity-log"', html)
        self.assertIn('id="detailPanelCompare"', html)
        self.assertIn('class="workspace"', html)

    def test_desktop_fixture_bundle_still_has_selected_detail(self) -> None:
        fixture = Path(__file__).resolve().parents[1] / "docs" / "examples" / "desktop" / "sample-desktop-ui-bundle.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertIn("selected_session_detail", payload)
        self.assertIsNotNone(payload["selected_session_detail"])
        self.assertIn("session", payload["selected_session_detail"])


if __name__ == "__main__":
    unittest.main()
