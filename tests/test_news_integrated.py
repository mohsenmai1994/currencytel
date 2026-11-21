"""Regression tests for the canonical (non-duplicate) news pipeline.

No real network requests or channel messages; check the exact API payloads.
"""
from __future__ import annotations
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from currencytel.news import formatting, image_fetch, pipeline
from currencytel.publishers import bale, rubika
from currencytel.publishers.base import PublishError

STORY = {
    "id": "abc123", "title": "خبر اقتصادی 🪙", "summary": "این خبر درباره اقتصاد است.",
    "source": "باشگاه خبرنگاران", "link": "https://example.com/news/1?x=1&y=2",
    "photo": "https://img.example.com/photo.jpg", "tags": ["#اقتصاد"],
    "published": "2026-11-21T18:00:00+00:00",
}


def jpg():
    img = Image.new("RGB", (320, 180), "orange")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_single_canonical_import_targets():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "news").exists()
    assert not (root / "publishers").exists()
    assert "send_news" in Path(pipeline.__file__).read_text()


def test_bale_caption_clickable_link_no_raw_article_url():
    caption = formatting.bale_caption(STORY)
    assert "<b>خبر اقتصادی 🪙</b>" in caption
    assert '<a href="https://example.com/news/1?x=1&amp;y=2">باشگاه خبرنگاران</a>' in caption
    assert "https://example.com/news" not in caption.replace('<a href="https://example.com/news/1?x=1&amp;y=2">', '')
    assert caption.endswith("#اقتصاد\n@currencytel")
    assert "**" not in caption


def test_rubika_caption_link_metadata_not_printed():
    text, metadata = formatting.rubika_caption_metadata(STORY)
    assert "https://example.com" not in text
    assert text.endswith("#اقتصاد\n@currencytel")
    spans = metadata["meta_data_parts"]
    assert {x["type"] for x in spans} == {"Bold", "Link"}
    link = next(x for x in spans if x["type"] == "Link")
    assert link["link_url"].startswith("https://example.com/news/1")
    assert link["length"] == len("باشگاه خبرنگاران")
    assert spans[0]["from_index"] == 3  # 📰 is 2 UTF-16 units + space


def test_bale_photo_html_upload(monkeypatch):
    monkeypatch.setenv("BALE_BOT_TOKEN", "sample")
    monkeypatch.setenv("BALE_CHAT_ID", "chan")
    monkeypatch.setattr(image_fetch, "first_usable_article_image", lambda *a, **k: (jpg(), "news.jpg", "image/jpeg"))
    payloads = []

    def fake_post(url, data, files, timeout):
        payloads.append((url, data, files))
        return SimpleNamespace(ok=True, status_code=200,
                               json=lambda: {"ok": True, "result": {"message_id": 123}})

    monkeypatch.setattr(bale.requests, "post", fake_post)
    receipt = bale.send_news(STORY)
    assert receipt.message_id == "123"
    assert payloads[0][0].endswith("/sendPhoto")
    assert payloads[0][1]["parse_mode"] == "HTML"
    assert payloads[0][2]["photo"][0] == "news.jpg"
    assert "<a href=" in payloads[0][1]["caption"]


def test_bale_no_photo_never_sends_text(monkeypatch):
    monkeypatch.setenv("BALE_BOT_TOKEN", "sample")
    monkeypatch.setenv("BALE_CHAT_ID", "chan")
    monkeypatch.setattr(image_fetch, "first_usable_article_image", lambda *a, **k: None)
    monkeypatch.setattr(bale.requests, "post", lambda *a, **k: pytest.fail("must not call API"))
    with pytest.raises(PublishError, match="NEWS_IMAGE_UNAVAILABLE"):
        bale.send_news(STORY)


def test_rubika_upload_then_linked_reply(monkeypatch):
    monkeypatch.setenv("RUBIKA_BOT_TOKEN", "sample")
    monkeypatch.setenv("RUBIKA_CHAT_ID", "c0123456789")
    monkeypatch.setattr(image_fetch, "first_usable_article_image", lambda *a, **k: (jpg(), "news.jpg", "image/jpeg"))
    calls = []

    def fake_api(token, method, payload, session=None):
        calls.append((method, payload))
        return {"requestSendFile": {"upload_url": "https://upload.example.com/abc"},
                "sendFile": {"message_id": "photo1"},
                "sendMessage": {"message_id": "reply1"}}[method]

    class Session:
        def post(self, url, files, timeout):
            assert url.startswith("https://upload.example.com/")
            assert files["file"][2] == "image/jpeg"
            return SimpleNamespace(ok=True, json=lambda: {"data": {"file_id": "file1"}})

    monkeypatch.setattr(rubika, "_api", fake_api)
    checkpoint = []
    receipt = rubika.send_news(STORY, session=Session(), on_photo_sent=checkpoint.append)
    assert receipt.message_id == "reply1"
    assert checkpoint == ["photo1"]
    assert [a[0] for a in calls] == ["requestSendFile", "sendFile", "sendMessage"]
    assert calls[-1][1]["reply_to_message_id"] == "photo1"
    assert "https://example.com/news" not in calls[-1][1]["text"]
    assert any(a["type"] == "Link" for a in calls[-1][1]["metadata"]["meta_data_parts"])


def test_rubika_reuses_checkpoint_without_upload(monkeypatch):
    monkeypatch.setenv("RUBIKA_BOT_TOKEN", "sample")
    monkeypatch.setenv("RUBIKA_CHAT_ID", "c0123456789")

    def fake_api(token, method, payload, session=None):
        assert method == "sendMessage"
        assert payload["reply_to_message_id"] == "old_photo"
        return {"message_id": "reply2"}

    monkeypatch.setattr(rubika, "_api", fake_api)
    assert rubika.send_news(STORY, previous_photo_id="old_photo").message_id == "reply2"


def test_replay_existing_news_and_pending_checkpoint(tmp_path, monkeypatch):
    # Replay is needed because old releases already marked text-only news as sent.
    data = tmp_path / "data"
    data.mkdir()
    (data / "news.json").write_text(json.dumps([STORY], ensure_ascii=False))
    (data / "news_state.json").write_text(json.dumps({"seen": {}, "pending": {}}))
    monkeypatch.setattr(pipeline, "DATA", data)
    monkeypatch.setattr(pipeline, "enabled_platforms", lambda: ["bale", "rubika"])
    sends = []

    def bale_send(story):
        sends.append("bale")

    def fail_rubika(story, on_photo_sent, previous_photo_id):
        sends.append(("rubika", previous_photo_id))
        on_photo_sent("pic-1")
        raise PublishError("Rubika formatted reply rejected")

    monkeypatch.setattr(pipeline, "CHANNELS", {"bale": bale_send, "rubika": fail_rubika})
    assert pipeline.run_news(replay_latest=True) == 1
    state = json.loads((data / "news_state.json").read_text())
    assert state["pending"]["abc123"] == ["rubika"]
    assert state["photos_sent"]["abc123:rubika"] == "pic-1"
    assert sends == ["bale", ("rubika", None)]

    def success_rubika(story, on_photo_sent, previous_photo_id):
        sends.append(("retry", previous_photo_id))
        assert previous_photo_id == "pic-1"

    monkeypatch.setattr(pipeline, "CHANNELS", {"bale": bale_send, "rubika": success_rubika})
    monkeypatch.setattr(pipeline, "select_story", lambda *args: None)
    assert pipeline.run_news(replay_latest=False) == 0
    state = json.loads((data / "news_state.json").read_text())
    assert state["pending"] == {}
    assert state["photos_sent"] == {}
    assert sends[-1] == ("retry", "pic-1")


def test_png_and_webp_normalize_to_jpeg():
    for fmt in ("PNG", "WEBP"):
        image = Image.new("RGBA", (300, 200), (20, 100, 180, 80))
        b = BytesIO(); image.save(b, format=fmt)
        output, name, mimetype = image_fetch.normalize_image(b.getvalue())
        assert output.startswith(b"\xff\xd8\xff")
        assert (name, mimetype) == ("news.jpg", "image/jpeg")


def test_invalid_image_bytes_are_rejected():
    with pytest.raises(ValueError, match="Image decoding failed"):
        image_fetch.normalize_image(b"not-a-picture")
