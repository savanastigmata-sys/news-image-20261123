# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/savanastigmata-sys/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/savanastigmata-sys/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

One picture summing up Monday 23 November 2026: 50 sourced stories across 7 regions and 16 fields, a UTC timeline that follows the day as it turns west, 16 lead stories each with its own procedurally drawn illustration, a world map with numbered pins and a per-region tally, and a date check that names what was left out (the big stories that belong to other dates) and what had not happened yet when the image was built, at about 16:00 UTC on 24 November. Every story here happened, or was first reported, on 23 November 2026 in at least one time zone. No story was invented; no story from another date is presented as a 23 November story. CLAIM means one side's account, not independently confirmed; every story is marked how sure it is.

The day's spine: Nvidia reinstates Jensen Huang as CEO and the shares jump 31%, adding about $950bn in a day; the COP31 fallout erupts in Canberra as Pacific nations despair; the EU unveils its 22nd Russia sanctions package; Zelenskyy confirms Ukrainian sea drones sank a Russian corvette off Libya; Indonesia confirms 24 dead in the Cikande candy-factory fire; Democrats reach 258 House seats, their biggest majority since 1992; Trump says Iran strikes may resume next year if talks fail.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Pure Python standard library: `main.py` draws a 1024x1024 PNG from DejaVu glyph bitmaps in `fontdata.py` (rasterised at build time, decoded at run time). No network, no clock, no randomness — two runs write identical bytes (verified: same sha256). Output is 59,474 bytes, well under the 1 MiB gate.

---

<sub>Entered on [make.fun](https://make.fun/?ref=6dbr02mm&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>
