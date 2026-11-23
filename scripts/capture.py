"""Optional evidence capture with a local Chromium browser and Playwright."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", required=True, type=Path)
    args = parser.parse_args()
    url = Path("reports/release/index.html").resolve().as_uri()
    output = Path("assets/web")
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(args.browser), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(url)
        assert page.get_by_role("heading", name="Escenario beneficioso · ship").is_visible()
        page.screenshot(path=output / "decision.png")
        page.get_by_text("Ver sensibilidad al costo por intento", exact=True).click()
        assert page.locator("details[open] tbody tr").count() == 3
        for target, label in [
            ("escenarios", "Escenarios"),
            ("incidente", "Incidente"),
            ("calibracion", "Calibración"),
        ]:
            page.get_by_role("link", name=label, exact=True).click()
            assert page.locator("#" + target).is_visible()
            page.screenshot(path=output / (target + ".png"))
        assert page.locator("#escenarios tbody tr").count() == 5
        assert page.locator("#calibracion tbody tr").count() == 5
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(url)
        overflow = page.evaluate("document.documentElement.scrollWidth>innerWidth")
        assert not overflow and not errors
        page.screenshot(path=output / "movil.png")
        import json

        Path("reports/browser.json").write_text(
            json.dumps(
                {
                    "browser": browser.version,
                    "js_errors": errors,
                    "mobile_horizontal_overflow": overflow,
                    "checked": [
                        "navigation",
                        "five scenarios",
                        "cost sensitivity",
                        "calibration",
                        "mobile layout",
                    ],
                },
                indent=2,
            ),
            encoding="utf8",
        )
        browser.close()


if __name__ == "__main__":
    main()
