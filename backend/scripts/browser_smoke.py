"""Opt-in browser check using real models and a server-local development clip.

Choose candidate numbers after inspecting the preview. Requires the optional
Playwright dependency in the YOLO environment. Evidence stays in runtime/.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--api", default="http://127.0.0.1:8001")
    parser.add_argument("--clip", required=True, help="Displayed clip name without its extension")
    parser.add_argument("--model", choices=["yolo", "mediapipe"], default="yolo")
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--max-frames", type=int, default=60)
    parser.add_argument("--candidates", type=int, nargs="*", default=[])
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("runtime/browser-evidence"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_default_timeout(60000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        page.get_by_role("button", name="Analyze a test clip", exact=True).click()
        name = "YOLO pose + ByteTrack" if args.model == "yolo" else "MediaPipe Pose Landmarker"
        page.get_by_role("radio", name=name, exact=True).click()
        page.get_by_role("radio").filter(has_text=args.clip).click()
        page.get_by_label("Starting frame", exact=True).fill(str(args.frame))
        with page.expect_response(lambda r: "/preview?" in r.url) as response:
            page.get_by_role("button", name="Load frame preview", exact=True).click()
        assert response.value.ok, response.value.text()
        preview = response.value.json()
        expect(page.get_by_label("Far-left x", exact=True)).to_be_visible()
        assert preview["corners_px"], "This smoke script needs a clip with saved corners. Mark them first."
        image = page.get_by_label(
            "Court preview; edit Far-left coordinates below for keyboard access", exact=True
        )
        image.scroll_into_view_if_needed()
        bounds = image.bounding_box()
        x, y = preview["corners_px"][0]
        image.click(
            position={
                "x": x / preview["source"]["width"] * bounds["width"],
                "y": y / preview["source"]["width"] * bounds["width"],
            }
        )
        assert abs(float(page.get_by_label("Far-left x", exact=True).input_value()) - x) < 1
        assert abs(float(page.get_by_label("Far-left y", exact=True).input_value()) - y) < 1
        # Also verify the complete keyboard-only calibration path.
        page.get_by_role("button", name="Reset corners", exact=True).click()
        expect(page.get_by_role("button", name="Analyze player positions", exact=True)).to_be_disabled()
        for name, point in zip(("Far-left", "Far-right", "Near-right", "Near-left"), preview["corners_px"]):
            for axis, value in zip(("x", "y"), point):
                page.get_by_label(f"{name} {axis}", exact=True).fill(str(value))
        if args.model == "yolo":
            for candidate in args.candidates:
                checkbox = page.get_by_role("checkbox", name=f"Player candidate {candidate}", exact=True)
                checkbox.focus()
                checkbox.press("Space")
                expect(checkbox).to_be_checked()
        page.get_by_label("Maximum frames", exact=True).fill(str(args.max_frames))
        page.get_by_text("Mark the four court corners", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / f"{args.model}-calibration.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        if args.preview_only:
            print(json.dumps({"preview": preview, "page_errors": errors}))
            browser.close()
            return
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/upload")) as posted:
            page.get_by_role("button", name="Analyze player positions", exact=True).click()
        request = posted.value.post_data_json
        if args.model == "yolo":
            assert request["analysis"]["selections"] == [
                preview["candidates"][i - 1]["bbox"] for i in sorted(args.candidates)
            ]
        assert request["analysis"]["start_frame"] == args.frame
        expect(page.get_by_text("Player tracking results", exact=True)).to_be_visible(timeout=180000)
        session_id = page.url.split("/session/")[1].split("/")[0]
        results = page.request.get(f"{args.api}/api/sessions/{session_id}/results").json()
        assert results["attempts_source"] == "unavailable" and results["attempts"] == []
        assert results["track"]["data_source"] == "model"
        expect(page.get_by_role("button", name="Publish to Profile", exact=True)).to_have_count(0)
        next_button = page.get_by_role("button", name="Next", exact=True)
        if results["track"]["frames"] > 1:
            next_button.click()
            expect(page.get_by_text("Sample 2 of", exact=False)).to_be_visible()
            page.get_by_role("button", name="Previous", exact=True).click()
            page.get_by_role("button", name="Play", exact=True).click()
            expect(page.get_by_text("Sample 2 of", exact=False)).to_be_visible()
            page.get_by_role("button", name="Pause", exact=True).click()
        if args.model == "yolo":
            summary_before = page.get_by_text("Missing positions", exact=True).locator("..").inner_text()
            page.get_by_role("radio", name="player 1", exact=True).click()
            expect(page.get_by_role("radio", name="player 1", exact=True)).to_be_checked()
            assert (
                page.get_by_text("Missing positions", exact=True).locator("..").inner_text() == summary_before
            )
        page.get_by_text("Court positions", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / f"{args.model}-results-mobile.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.set_viewport_size({"width": 1280, "height": 900})
        page.screenshot(path=str(args.output / f"{args.model}-results-desktop.png"))
        artifact = page.request.get(f"{args.api}/api/sessions/{session_id}/artifacts/track.json")
        assert artifact.ok and len(artifact.json()) == results["track"]["observations"]
        # Exercise the visible download control, not only its endpoint.
        with page.expect_download() as download:
            page.get_by_role("button", name="Download track.csv", exact=True).click()
        download.value.save_as(args.output / f"{args.model}-track.csv")
        assert not errors, errors
        report = {
            "session_id": session_id,
            "results": results,
            "checks": [
                "real model and clip selection",
                "pointer and keyboard calibration",
                "original pixel selections at 390px width",
                "real inference and shared projection",
                "playback and filtering",
                "download control",
                "unavailable attempt scores",
                "no horizontal overflow",
                "no JavaScript page errors",
            ],
        }
        (args.output / f"{args.model}-browser.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
