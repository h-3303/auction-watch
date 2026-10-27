from datetime import datetime, timedelta, timezone

from auction_watch import core, scan, state, notify

UTC = timezone.utc
NOW = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)


def row(**kw):
    base = {"Domain Name": "TOOLADVISOR.COM", "ItemID": "733205750", "Price": "$1", "Bids": "1",
            "Domain Age": "14", "ValuationPrice": "$3,248", "Exact Match TLDs": "16",
            "Time Left": "10/27/2026 10:47 AM (PDT)"}
    base.update(kw)
    return base


def test_screen_keeps_an_aged_valued_cheap_dotcom_closing_today():
    c = scan.screen(row(), NOW)
    assert c["domain"] == "tooladvisor.com" and c["price"] == 1 and c["item_id"] == "733205750"


def test_screen_rejects_young_names_cheap_valuations_and_few_tlds():
    assert scan.screen(row(**{"Domain Age": "3"}), NOW) is None
    assert scan.screen(row(ValuationPrice="$900"), NOW) is None
    assert scan.screen(row(**{"Exact Match TLDs": "2"}), NOW) is None


def test_screen_rejects_digits_hyphens_and_other_tlds():
    assert scan.screen(row(**{"Domain Name": "TOOL-ADVISOR.COM"}), NOW) is None
    assert scan.screen(row(**{"Domain Name": "TOOLADVISOR.IO"}), NOW) is None


def test_screen_rejects_auctions_outside_the_next_36_hours():
    assert scan.screen(row(**{"Time Left": "10/30/2026 10:47 AM (PDT)"}), NOW) is None
    assert scan.screen(row(**{"Time Left": "10/27/2026 06:30 AM (PDT)"}), NOW) is None


def test_screen_rejects_brand_lookalikes():
    assert scan.screen(row(**{"Domain Name": "DEEPLM.COM"}), NOW) is None
    assert scan.screen(row(**{"Domain Name": "NETFLIXHUB.COM"}), NOW) is None


def test_pick_watches_when_a_fifth_of_the_estimate_clears_the_price():
    c = scan.screen(row(), NOW)
    item = scan.pick(c, auction_estimate=390)
    assert item["max_bid"] == core.max_bid(390) and item["domain"] == "tooladvisor.com"
    assert item["url"].endswith("tooladvisor-com-733205750")
    assert scan.pick(c, auction_estimate=40) is None


def test_merge_keeps_alert_flags_and_drops_closed_items():
    old = [{"domain": "a.com", "close": (NOW + timedelta(hours=1)).isoformat(), "alerted": True},
           {"domain": "gone.com", "close": (NOW - timedelta(days=2)).isoformat()}]
    new = [{"domain": "a.com", "close": (NOW + timedelta(hours=1)).isoformat()},
           {"domain": "b.com", "close": (NOW + timedelta(hours=5)).isoformat()}]
    merged = {i["domain"]: i for i in scan.merge(old, new, NOW)}
    assert merged["a.com"]["alerted"] is True and "b.com" in merged and "gone.com" not in merged


def test_state_round_trips_through_encryption():
    key = state.new_key()
    blob = state.seal({"watch": [1, 2]}, key)
    assert b"watch" not in blob and state.unseal(blob, key) == {"watch": [1, 2]}


def test_push_request_targets_the_topic_with_title_and_click_url():
    url, headers, data = notify.request("aw-topic", "t", "b", click="https://x")
    assert url == "https://ntfy.sh/aw-topic" and headers["Title"] == "t" and headers["Click"] == "https://x"
    assert data == b"b"


def test_screen_requires_one_or_two_common_english_words():
    for good in ("TOOLADVISOR.COM", "THEVAULTS.COM", "BITSITES.COM", "LIFEFIELD.COM", "HOTELVOICE.COM"):
        assert scan.screen(row(**{"Domain Name": good}), NOW) is not None, good
    for junk in ("RNGGC.COM", "ZENOVARX.COM", "JOYUAN.COM", "QSCOT.COM", "SESE.CO"):
        assert scan.screen(row(**{"Domain Name": junk}), NOW) is None, junk


def test_screen_rejects_net_org_and_adult_or_gambling_themes():
    assert scan.screen(row(**{"Domain Name": "YOURMORTGAGE.NET"}), NOW) is None
    assert scan.screen(row(**{"Domain Name": "ZOOPHILIST.COM"}), NOW) is None
    assert scan.screen(row(**{"Domain Name": "CASINOWIN.COM"}), NOW) is None
