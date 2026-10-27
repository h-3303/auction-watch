"""The two jobs, with every outside dependency passed in."""
from . import core, scan as screening

MAX_LOOKUPS = 40  # valuation lookups per scan, best GoDaddy valuations first
MAX_FAILURES = 3  # consecutive failed lookups before giving up on HumbleWorth for this scan
GEM_FLOOR = 400  # investor-auction estimate worth an $11 registration


def gems(st, found, push):
    seen = st.setdefault("gems_seen", [])
    fresh = [(d, e) for d, e in found if e >= GEM_FLOOR and d not in seen]
    if fresh:
        lines = [f"{d}: est ${e}, register for ~$11" for d, e in fresh]
        push(f"{len(fresh)} registrable domain{'s' if len(fresh) > 1 else ''} worth a look", "\n".join(lines),
             "https://humbleworth.com/gems")
        seen.extend(d for d, _ in fresh)
    return fresh


def tick(st, now, price_of, push):
    changed = False
    for item in st["watch"]:
        if not core.is_due(item, now):
            continue
        price = price_of(item["domain"])
        if core.decide(item, price) == "send":
            title, body = core.message(item, price, now)
            push(title, body, item["url"])
        else:
            item["suppressed_at"] = price
        item["alerted"] = True
        changed = True
    return changed


def scan(st, rows, now, estimate_of, push):
    candidates = [c for c in (screening.screen(r, now) for r in rows) if c]
    candidates.sort(key=lambda c: -c["valuation"])
    watched = {i["domain"] for i in st["watch"]}
    picks, considered, failures = [], 0, 0
    for c in candidates:
        if c["domain"] in watched:
            continue
        if considered >= MAX_LOOKUPS:
            break
        considered += 1
        estimate = estimate_of(c["domain"]) if failures < MAX_FAILURES else None
        source = "humbleworth"
        if estimate is None:
            failures += 1
            # HumbleWorth unreachable: GoDaddy's valuation runs high, so a tenth of it stands in.
            estimate, source = c["valuation"] / 10, "godaddy"
        else:
            failures = 0
        item = screening.pick(c, estimate)
        if item:
            item["estimate_source"] = source
            picks.append(item)
    st["watch"] = screening.merge(st["watch"], picks, now)
    if picks:
        lines = [f"{i['domain']}: ${i['last_price']} now, max ${i['max_bid']} (est ${i['auction_estimate']})"
                 for i in picks]
        push(f"{len(picks)} new auction pick{'s' if len(picks) > 1 else ''}", "\n".join(lines), None)
    return picks
