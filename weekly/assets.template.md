# Per-asset notes

Commentary and news for the chart modals. Each heading is one instrument;
anything you do not write about simply has no commentary box in its modal.

Head a section with the name or the ticker — "Apple" or "AAPL", "USD/ZAR",
"HY Spread" — whichever is quicker. Never the internal slug. A heading that
matches nothing is reported when you run the script, so typos surface rather
than vanishing.

News lines are:

    - YYYY-MM-DD | Headline | https://...

The date is the point: it is how a reader tells a piece written this week from
one carried over because the week was quiet. The URL is optional — leave it
off and the headline shows as plain text.

After editing, run:

    python update_commentary.py

Everything above the first "### " is ignored. Delete the example below.

### AAPL

One or two sentences on what moved this name and why.

News:
- 2026-10-09 | Example headline, delete me | https://example.com
