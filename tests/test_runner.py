from datetime import datetime, timedelta, timezone

from auction_watch import runner

UTC = timezone.utc
NOW = datetime(2026, 10, 27, 16, 40, tzinfo=UTC)


def item(domain, minutes, max_bid=80, **kw):
    return {"domain": domain, "close": (NOW + timedelta(minutes=minutes)).isoformat(), "max_bid": max_bid,
            "url": f"https://x/{domain}", "last_price": 1, **kw}


def test_tick_pushes_due_items_with_live_price_and_marks_them():
    pushed = []
    st = {"watch": [item("a.com", 28), item("later.com", 120)]}
    runner.tick(st, NOW, price_of=lambda d: 15, push=lambda *a: pushed.append(a))
    assert len(pushed) == 1 and pushed[0][0] == "a.com closes in 28 min" and "Now $15" in pushed[0][1]
    assert st["watch"][0]["alerted"] is True and not st["watch"][1].get("alerted")


def test_tick_stays_silent_when_price_is_over_max_but_marks_it_handled():
    pushed = []
    st = {"watch": [item("a.com", 28, max_bid=80)]}
    runner.tick(st, NOW, price_of=lambda d: 95, push=lambda *a: pushed.append(a))
    assert pushed == [] and st["watch"][0]["alerted"] is True and st["watch"][0]["suppressed_at"] == 95


def test_tick_reports_whether_state_changed():
    st = {"watch": [item("later.com", 120)]}
    assert runner.tick(st, NOW, price_of=lambda d: 1, push=lambda *a: None) is False


def test_scan_adds_new_picks_and_pushes_one_digest():
    rows = [{"Domain Name": "TOOLADVISOR.COM", "ItemID": "733205750", "Price": "$1", "Bids": "1",
             "Domain Age": "14", "ValuationPrice": "$3,248", "Exact Match TLDs": "16",
             "Time Left": "10/28/2026 10:47 AM (PDT)"}]
    pushed = []
    st = {"watch": []}
    runner.scan(st, rows, NOW, estimate_of=lambda d: 390, push=lambda *a: pushed.append(a))
    assert [i["domain"] for i in st["watch"]] == ["tooladvisor.com"]
    assert len(pushed) == 1 and "tooladvisor.com" in pushed[0][1] and "max $75" in pushed[0][1]


def test_scan_does_not_repeat_picks_already_watched():
    rows = [{"Domain Name": "TOOLADVISOR.COM", "ItemID": "733205750", "Price": "$1", "Bids": "1",
             "Domain Age": "14", "ValuationPrice": "$3,248", "Exact Match TLDs": "16",
             "Time Left": "10/28/2026 10:47 AM (PDT)"}]
    pushed = []
    st = {"watch": []}
    runner.scan(st, rows, NOW, estimate_of=lambda d: 390, push=lambda *a: None)
    runner.scan(st, rows, NOW, estimate_of=lambda d: 390, push=lambda *a: pushed.append(a))
    assert pushed == [] and len(st["watch"]) == 1


def test_scan_falls_back_to_godaddy_valuation_after_three_failed_lookups():
    rows = [{"Domain Name": f"{n}.COM", "ItemID": str(k), "Price": "$1", "Bids": "0", "Domain Age": "14",
             "ValuationPrice": "$3,250", "Exact Match TLDs": "16", "Time Left": "10/28/2026 10:47 AM (PDT)"}
            for k, n in enumerate(["toolhub", "bluefield", "silverlake", "redwood", "stonebridge"])]
    calls = []
    st = {"watch": []}
    runner.scan(st, rows, NOW, estimate_of=lambda d: calls.append(d), push=lambda *a: None)
    assert len(calls) == 3
    assert len(st["watch"]) == 5 and all(i["max_bid"] == 65 for i in st["watch"])
    assert all(i["estimate_source"] == "godaddy" for i in st["watch"])
