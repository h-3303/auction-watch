from datetime import datetime, timedelta, timezone

from auction_watch import core

UTC = timezone.utc


def test_parse_close_uses_the_offset_godaddy_labels():
    assert core.parse_close("10/27/2026 10:09 AM (PDT)") == datetime(2026, 10, 27, 17, 9, tzinfo=UTC)
    assert core.parse_close("11/02/2026 01:46 PM (PST)") == datetime(2026, 11, 2, 21, 46, tzinfo=UTC)


def test_max_bid_is_a_fifth_of_the_auction_estimate_rounded_down_to_five():
    assert core.max_bid(468) == 90
    assert core.max_bid(1960) == 390
    assert core.max_bid(40) == 5


def _item(close, **kw):
    return {"domain": "bitsites.com", "close": close.isoformat(), "max_bid": 80, "url": "https://x/bitsites", **kw}


def test_item_is_due_inside_the_last_35_minutes():
    now = datetime(2026, 10, 27, 16, 40, tzinfo=UTC)
    assert core.is_due(_item(now + timedelta(minutes=29)), now)
    assert not core.is_due(_item(now + timedelta(minutes=50)), now)
    assert not core.is_due(_item(now - timedelta(minutes=1)), now)


def test_item_already_alerted_is_not_due_again():
    now = datetime(2026, 10, 27, 16, 40, tzinfo=UTC)
    assert not core.is_due(_item(now + timedelta(minutes=20), alerted=True), now)


def test_price_above_max_suppresses_the_alert():
    assert core.decide(_item(datetime.now(UTC)), price=81) == "suppress"
    assert core.decide(_item(datetime.now(UTC)), price=80) == "send"
    assert core.decide(_item(datetime.now(UTC)), price=None) == "send"


def test_message_shows_live_price_max_and_minutes_left():
    now = datetime(2026, 10, 27, 16, 40, tzinfo=UTC)
    title, body = core.message(_item(now + timedelta(minutes=29)), price=12, now=now)
    assert title == "bitsites.com closes in 29 min"
    assert "Now $12" in body and "max $80" in body and "https://x/bitsites" in body


def test_message_says_when_live_price_is_unknown():
    now = datetime(2026, 10, 27, 16, 40, tzinfo=UTC)
    _, body = core.message(_item(now + timedelta(minutes=29), last_price=1), price=None, now=now)
    assert "live price unavailable" in body and "$1" in body
