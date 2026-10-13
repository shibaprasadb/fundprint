"""The Home page: sample data first, then the upload and the request-a-statement checklist."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))  # the app imports `ui` directly

import ui  # noqa: E402

CAMS = "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement"


@pytest.fixture
def home():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=90)
    at.run()
    assert not at.exception
    return at


def test_order_is_promise_then_sample_then_own_statement(home):
    kinds = [e.type for e in home.main]
    text = {i: getattr(e, "value", "") for i, e in enumerate(home.main)}
    promise = next(i for i, v in text.items() if "Nothing is stored. Your file is read and dropped" in str(v))
    sample = kinds.index("button")
    own = next(i for i, v in text.items() if "Use your own statement" in str(v))
    assert promise < sample < own
    assert home.button[0].label == "See it with sample data"
    assert home.button[0].proto.type == "primary"
    assert "A made-up portfolio, so you can see what Fundprint shows before using your own." in [c.value for c in home.caption]


def test_upload_box_sits_above_the_note_and_checklist(home):
    kinds = [e.type for e in home.main]
    assert home.subheader[0].value == "Already have your statement?"
    assert kinds.index("file_uploader") < kinds.index("code") < kinds.index("link_button")


def test_checklist_has_four_steps(home):
    assert [s.value for s in home.subheader[1:]] == [
        "Step 1. Open the CAMS statement page", "Step 2. Fill in the form like this",
        "Step 3. Check your email", "Step 4. Come back and upload it",
    ]


def test_cams_button_goes_to_the_cams_page(home):
    (button,) = home.get("link_button")   # Streamlit opens link buttons in a new tab
    assert button.proto.url == CAMS
    assert button.proto.label == "Open CAMS statement page ↗"


def test_come_back_note_shows_a_copyable_link(home):
    assert [c.value for c in home.code] == ["https://lab.shibaprasadb.com/fundprint"]


def test_form_table_matches_the_spec(home):
    table = next(m.value for m in home.markdown if "| Field | Choose | Note |" in m.value)
    for cell in ("**Detailed** (includes transaction listing)", "**Required.** A Summary statement won't work.",
                 "**A date before your first-ever investment**", "Earlier is fine. Missing history makes results wrong.",
                 "**Something simple you'll remember**", "You'll type it here once. Fundprint never stores it."):
        assert cell in table
    for marker in ("① Statement type", "② Period / from date", "③ Password"):
        assert marker in table


def test_step_text_says_statement_not_cas(home):
    steps = " ".join(m.value for m in home.markdown if "Field | Choose" in m.value or "usually arrives" in m.value)
    assert "CAS" not in steps


def test_screenshot_is_shown_with_alt_text_when_the_file_exists(home):
    html = " ".join(m.value for m in home.markdown)
    assert ui.FORM_IMAGE.exists() and ui.FORM_IMAGE_ALT in html


def test_screenshot_slot_is_skipped_cleanly_without_the_file(monkeypatch):
    monkeypatch.setattr(ui, "FORM_IMAGE", ROOT / "app/assets/missing.png")
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=90)
    at.run()
    assert not at.exception and not at.error
    assert not any(ui.FORM_IMAGE_ALT in m.value for m in at.markdown)
    assert len(at.subheader) == 5   # the checklist still shows all four steps
