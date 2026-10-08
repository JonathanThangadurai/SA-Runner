# SA-Runner

Fork of [Apoorvanp/SA-Runner](https://github.com/Apoorvanp/SA-Runner). This fork's
`solar-and-demand-response` branch replaces every synthetic production/consumption value
with a real one:

- **`real_data.py`**: 36 real households' actual metered solar production and consumption,
  replayed half-hour by half-hour. No formula, no random number generator - see "The data"
  below for provenance and the one real limitation worth knowing about.
- **`producer-sync.py`**: production is each house's real recorded solar output (`GG`) at the
  current real half-hour. Zero at night is now an actual measurement, not a curve's limit.
- **`consumer-sync.py`**: consumption is each house's real recorded usage (`GC`) at the current
  real half-hour, scaled by how cheap or expensive the live NL day-ahead price
  ([eu-power-poc](https://github.com/JonathanThangadurai/eu-power-poc)'s `/price/current`) is
  right now - demand roughly doubles when the real price is cheap, roughly halves when it's
  expensive (clamped 0.3x-2.0x). A real empirical baseline plus a price-elasticity overlay,
  rather than either alone.

The price lookup is read once per outer loop iteration (not once per house) to avoid hammering
eu-power-poc every 2 seconds.

## The data

**Source**: [Ausgrid's "Solar home electricity data"](https://www.data.gov.au/data/en/dataset/nsw-solar-home-electricty-data) -
300 real households in Sydney, Australia, each with a gross-metered rooftop solar install,
recording actual consumption (`GC`) and actual solar generation (`GG`) every 30 minutes for a
full year (1 July 2010 - 30 June 2011). Published by Ausgrid under
[CC BY 3.0 Australia](https://creativecommons.org/licenses/by/3.0/au/).

**Why a mirror, not the original URL**: Ausgrid's own hosting of this dataset is gone (confirmed
404 as of October 2026 - checked directly before relying on it). Only the metadata record survives
at data.gov.au. `data/ausgrid_subset.json.gz` in this repo was extracted from a self-hosted
archival copy of the original files, which preserves their original 2014-2017 file timestamps -
checked against the raw CSV's known values (e.g. Customer 1's recorded consumption on 2010-07-01)
to confirm the mirror matches the original byte-for-byte on the rows this project uses, not just
trusted on reputation.

**What's shipped**: only the 36 of the 300 households with *zero* missing days across the full
year (139 qualify; the first 36 by customer ID are used, one per community/house slot - see
`assigned_customer_id()`), and only the `GC`/`GG` categories (the dataset's third category, `CL`,
is a separate controlled-load circuit like hot water that this project has no use for). That's
1.49MB compressed - small enough to commit directly, so this runs fully offline with zero network
dependency on Ausgrid or its mirror at runtime.

**The one real limitation - read before citing this as "live Dutch household data"**: these are
real Sydney households, not real Dutch ones. Sydney is the Southern Hemisphere; this project's
price data is for the Netherlands, Northern Hemisphere - Sydney's summer is Amsterdam's winter.
Naively replaying the same calendar date would mean a real NL summer (lots of sun) incorrectly
replaying a real Sydney *winter* day (little sun), directly contradicting the real NL price signal
this project also uses. `real_data.py` shifts every lookup date by ~6 months before indexing into
the Ausgrid year, so "today, in NL" always replays the Ausgrid date sitting at the equivalent point
of *Sydney's own* seasonal cycle - a real household's real measurement, correctly season-aligned,
not literally today's Dutch weather. See `tests/test_real_data.py` for this verified directly
(NL July maps into the dataset's January).

## Installation
```shell
docker build -t producer:1.0 --target producer .
docker build -t consumer:1.0 --target consumer .
docker run -e HOST=http://host.docker.internal:8080 producer:1.0
docker run -e HOST=http://host.docker.internal:8080 -e EU_PRICE_API_URL=http://host.docker.internal:8001 consumer:1.0
```

### Tests

```shell
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v     # includes a known-value check against the raw Ausgrid CSV, and the season-shift logic
ruff check .
```

### Environment variables

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `HOST` | both | required | SA-Marketplace base URL |
| `EU_PRICE_API_URL` | consumer | `http://localhost:8001` | eu-power-poc base URL, for demand response |
| `REFERENCE_PRICE_EUR_PER_KWH` | consumer | `0.15` | "normal" price used to center the demand-response factor |
| `SOLAR_TZ` | both | `Europe/Amsterdam` | timezone the real-data replay and price lookups are keyed to |
