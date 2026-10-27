# auction-watch

Watches GoDaddy expired-domain auctions and sends push alerts (ntfy) without a computer switched on.

- **scan** (twice daily): screens GoDaddy's auction inventory (age ≥ 8, GoDaddy value ≥ $2k, exact match on ≥ 5 other TLDs, bid ≤ $30, closing within 36 h, no brand look-alikes), values the best 40 on HumbleWorth, and watches those whose cap (a fifth of the investor-auction estimate) clears the bid by $10. Also pushes newly dropped .coms worth ≥ $400 that can be registered at the normal fee.
- **tick** (every 5 min): 30–35 min before a watched auction closes, checks the live bid through GoDaddy's Auctions API and pushes "closes in N min, now $X, max $Y". If the bid is above the cap, it stays silent.

The watchlist lives in `state.enc`, Fernet-encrypted with the `STATE_KEY` secret; logs never print domain names.
Secrets: `STATE_KEY`, `NTFY_TOPIC`, optional `GODADDY_KEY` and `GODADDY_SECRET` (Classic Developer Key).

```
uv run pytest                     # tests
uv run auction-watch show         # list the watchlist (needs STATE_KEY)
```
