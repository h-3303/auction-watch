"""Network adapters. Kept thin: all decisions live in core/scan/runner."""
import csv
import io
import json
import os
import re
import tempfile
import urllib.request
import zipfile

INVENTORY = "https://inventory.auctions.godaddy.com/bidding_service_auctions.csv.zip"
HW = "https://humbleworth.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0 Safari/537.36"


def godaddy_rows():
    """Yield every live GoDaddy auction as a dict keyed by the CSV's (stripped) headers."""
    with tempfile.TemporaryFile() as tmp:
        req = urllib.request.Request(INVENTORY, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            while chunk := r.read(1 << 20):
                tmp.write(chunk)
        tmp.seek(0)
        with zipfile.ZipFile(tmp) as z, z.open(z.namelist()[0]) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline=""))
            header = [h.strip() for h in next(reader)]
            for row in reader:
                if len(row) >= len(header):
                    yield dict(zip(header, row))


def _dollars(text):
    return int(text.replace("$", "").replace(",", ""))


class HumbleWorth:
    """Investor-auction estimates from humbleworth.com, read through a headless browser."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self.page = self._browser.new_page(user_agent=UA)
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def estimate(self, domain):
        try:
            self.page.goto(f"{HW}/valuation/single?domain={domain}", wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_function(
                "() => /Fast sale \\(auction\\)\\s*\\$[\\d,]+/.test(document.querySelector('main')?.innerText||'')",
                timeout=20000)
            text = self.page.inner_text("main")
            m = re.search(r"Fast sale \(auction\)\s*(\$[\d,]+)", text)
            return _dollars(m.group(1)) if m else None
        except Exception:
            return None

    def gems(self):
        """(domain, estimate) for each dropped .com still available to register."""
        try:
            self.page.goto(f"{HW}/gems", wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_selector('a[href*="/valuation/single?domain="]', timeout=20000)
            cards = self.page.eval_on_selector_all(
                'a[href*="/valuation/single?domain="]',
                "els => els.map(a => [a.href, (a.closest('li')||a.parentElement).innerText])")
        except Exception:
            return []
        out = []
        for href, text in cards:
            m = re.search(r"domain=([a-z0-9.-]+)", href)
            v = re.search(r"Estimated auction value\s*(\$[\d,]+)", text)
            if m and v and "AVAILABLE" in text.upper():
                out.append((m.group(1), _dollars(v.group(1))))
        return out


def live_price(domain):
    """Current bid via GoDaddy's Auctions API, or None when no key is configured or the call fails."""
    key, secret = os.environ.get("GODADDY_KEY"), os.environ.get("GODADDY_SECRET")
    if not (key and secret):
        return None
    url = "https://api.godaddy.com/v1/customers/MY/aftermarket/listings/available?includes=listing"
    req = urllib.request.Request(url, data=json.dumps({"domains": [domain]}).encode(), method="POST",
                                 headers={"Authorization": f"sso-key {key}:{secret}",
                                          "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return _price_from(json.load(r), domain)
    except Exception:
        return None


def _price_from(payload, domain):
    """Find a current-price field for `domain` in the API response, whatever its exact nesting."""
    def walk(node):
        if isinstance(node, dict):
            if str(node.get("domainName", node.get("domain", ""))).lower() == domain:
                for k in ("currentPrice", "currentBid", "price", "bidAmount"):
                    if k in node:
                        v = node[k]
                        v = v.get("amount", v.get("value")) if isinstance(v, dict) else v
                        v = float(v)
                        return int(v / 1_000_000) if v >= 100_000 else int(v)  # micro-units; no watched bid nears $100k
            for child in node.values():
                if (found := walk(child)) is not None:
                    return found
        elif isinstance(node, list):
            for child in node:
                if (found := walk(child)) is not None:
                    return found
        return None
    return walk(payload)
