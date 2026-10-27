"""Screen GoDaddy auction rows into a watchlist."""
import re
from datetime import datetime, timedelta

from . import core

TLDS = {"com", "co"}
HORIZON = timedelta(hours=36)
MIN_LEAD = timedelta(hours=1)
# Labels that read as someone else's brand; owning these invites a dispute, not a sale.
BRANDS = ("deepl", "netflix", "google", "amazon", "apple", "facebook", "instagram", "tiktok", "openai",
          "chatgpt", "paypal", "microsoft", "youtube", "disney", "nike", "adidas", "tesla", "ticktick",
          "leatherman", "ebay", "walmart", "spotify", "samsung", "nvidia", "anthropic", "claude")
# Themes no end user pays a premium for in the open market (and that are unpleasant to hold).
BANNED = ("sex", "porn", "xxx", "zoo", "casino", "slot", "bet", "poker", "capsa", "nude", "escort", "drug")
MIN_ZIPF = 3.0  # wordfreq frequency: ~1 use per million words or more


def _common(word):
    from wordfreq import zipf_frequency
    return len(word) >= 2 and zipf_frequency(word, "en") >= MIN_ZIPF


def is_words(label):
    """True when the label is one common English word or two of them run together."""
    if _common(label):
        return True
    return any(_common(label[:i]) and _common(label[i:]) for i in range(3, len(label) - 2))


def _money(text):
    return float(str(text).replace("$", "").replace(",", "").strip() or 0)


def screen(row, now):
    name = row["Domain Name"].strip().lower()
    label, _, tld = name.partition(".")
    if tld not in TLDS or not re.fullmatch(r"[a-z]{3,12}", label):
        return None
    if any(b in label for b in BRANDS + BANNED) or not is_words(label):
        return None
    if int(row["Domain Age"] or 0) < 8 or _money(row["ValuationPrice"]) < 2000:
        return None
    if int(row["Exact Match TLDs"] or 0) < 5:
        return None
    price = _money(row["Price"])
    if price > 30:
        return None
    close = core.parse_close(row["Time Left"])
    if not (now + MIN_LEAD <= close <= now + HORIZON):
        return None
    return {"domain": name, "item_id": row["ItemID"].strip(), "price": int(price),
            "close": close.isoformat(), "valuation": int(_money(row["ValuationPrice"]))}


def pick(candidate, auction_estimate):
    cap = core.max_bid(auction_estimate)
    if cap < candidate["price"] + 10:
        return None
    slug = candidate["domain"].replace(".", "-")
    return {"domain": candidate["domain"], "close": candidate["close"], "max_bid": cap,
            "last_price": candidate["price"], "auction_estimate": int(auction_estimate),
            "item_id": candidate["item_id"],
            "url": f"https://www.godaddy.com/domain-auctions/{slug}-{candidate['item_id']}"}


def merge(old, new, now):
    keep = {i["domain"]: i for i in old if datetime.fromisoformat(i["close"]) > now - timedelta(days=1)}
    for item in new:
        if item["domain"] in keep:
            keep[item["domain"]] = {**item, **{k: v for k, v in keep[item["domain"]].items() if k == "alerted"}}
        else:
            keep[item["domain"]] = item
    return list(keep.values())
