"""Regression guard for KeepMore's accessible action-button palette."""
from pathlib import Path
import re

APP = Path(__file__).resolve().parents[1] / "app.py"
APP_TEXT = APP.read_text(encoding="utf-8")
CSS = re.search(r'st\.markdown\("""<style>(.*?)</style>""",unsafe_allow_html=True\)', APP_TEXT, re.S).group(1)


def luminance(hexcolor):
    rgb = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return sum(weight * value for weight, value in zip((0.2126, 0.7152, 0.0722), linear))


def contrast_ratio(first, second):
    brighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (brighter + 0.05) / (darker + 0.05)


def test_button_text_contrast_meets_wcag_aa():
    palettes = {
        "primary": ("#0a7f69", "#ffffff"),
        "primary hover": ("#086452", "#ffffff"),
        "secondary": ("#ffffff", "#14343c"),
        "secondary hover": ("#e9f6f2", "#14343c"),
        "disabled": ("#dceae6", "#47615e"),
    }
    for state, (background, foreground) in palettes.items():
        assert background in CSS and foreground in CSS, f"Missing {state} palette"
        assert contrast_ratio(background, foreground) >= 4.5, state


def test_controls_have_scoped_nested_label_styles():
    assert ':is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button *' in CSS
    assert 'currentColor !important' in CSS
    assert 'button:focus-visible' in CSS
    assert 'button:disabled' in CSS
    assert not re.search(r"(?m)^\s*p\s*\{color:", CSS), "Global paragraph style would affect buttons"


def test_workspace_switcher_uses_explicit_buttons():
    assert 'workspace_demo' in APP_TEXT
    assert 'workspace_personal' in APP_TEXT
    assert 'Explore demo' in APP_TEXT
    assert 'My money' in APP_TEXT
