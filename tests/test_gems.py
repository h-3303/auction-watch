from auction_watch import runner


def test_gems_pushes_registrable_names_worth_400_plus_once():
    st = {"watch": [], "gems_seen": []}
    pushed = []
    gems = [("howforward.com", 757), ("cheap.com", 60)]
    runner.gems(st, gems, push=lambda *a: pushed.append(a))
    runner.gems(st, gems, push=lambda *a: pushed.append(a))
    assert len(pushed) == 1 and "howforward.com" in pushed[0][1] and "cheap.com" not in pushed[0][1]
    assert st["gems_seen"] == ["howforward.com"]
