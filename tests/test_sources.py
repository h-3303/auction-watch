from auction_watch import sources


def test_price_is_found_in_nested_listing_and_converted_from_micro_units():
    payload = {"domains": [{"domain": "bitsites.com", "status": "AVAILABLE",
                            "listing": {"domainName": "bitsites.com", "currentPrice": 12_000_000}}]}
    assert sources._price_from(payload, "bitsites.com") == 12


def test_plain_dollar_price_is_returned_as_is():
    payload = [{"domainName": "veil.co", "price": 85}]
    assert sources._price_from(payload, "veil.co") == 85


def test_missing_domain_gives_none():
    assert sources._price_from({"domains": []}, "veil.co") is None


def test_one_dollar_in_micro_units_is_one_dollar():
    assert sources._price_from([{"domainName": "a.com", "currentPrice": 1_000_000}], "a.com") == 1
