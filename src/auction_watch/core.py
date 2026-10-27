"""Pure decision rules: no network, no clock reads, no files."""
from datetime import datetime, timedelta, timezone

OFFSETS = {"PDT": -7, "PST": -8}
ALERT_WINDOW = timedelta(minutes=35)


def parse_close(text):
    """GoDaddy's 'MM/DD/YYYY HH:MM AM (PDT)' -> aware UTC datetime, trusting the label's offset."""
    stamp, label = text.rsplit("(", 1)
    local = datetime.strptime(stamp.strip(), "%m/%d/%Y %I:%M %p")
    offset = timezone(timedelta(hours=OFFSETS[label.rstrip(")").strip()]))
    return local.replace(tzinfo=offset).astimezone(timezone.utc)


def max_bid(auction_estimate):
    """A fifth of the investor-auction estimate, rounded down to $5, never below $5."""
    return max(5, int(auction_estimate / 5) // 5 * 5)


def _close(item):
    return datetime.fromisoformat(item["close"])


def is_due(item, now):
    left = _close(item) - now
    return not item.get("alerted") and timedelta(0) < left <= ALERT_WINDOW


def decide(item, price):
    return "suppress" if price is not None and price > item["max_bid"] else "send"


def message(item, price, now):
    minutes = int((_close(item) - now).total_seconds() // 60)
    title = f"{item['domain']} closes in {minutes} min"
    if price is None:
        now_txt = f"live price unavailable (last seen ${item.get('last_price', '?')})"
    else:
        now_txt = f"Now ${price}"
    return title, f"{now_txt}, max ${item['max_bid']}. {item['url']}"
