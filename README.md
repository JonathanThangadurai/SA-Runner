# SA-Runner

Fork of [Apoorvanp/SA-Runner](https://github.com/Apoorvanp/SA-Runner). This fork's
`solar-and-demand-response` branch replaces the flat-random production/consumption with two
signals driven by real data from [eu-power-poc](https://github.com/JonathanThangadurai/eu-power-poc):

- **`producer-sync.py`**: production now follows a solar curve (zero at night, peaking at local
  solar noon) instead of a flat random amount at all hours - houses only have surplus to sell when
  real solar panels would too.
- **`consumer-sync.py`**: consumption now scales against the live NL day-ahead price fetched
  directly from eu-power-poc's `/price/current` - demand roughly doubles when the real price is
  cheap and roughly halves when it's expensive (clamped to 0.3x-2.0x so it never goes to zero or
  runs away). This is genuine demand response: the simulation reacts to an external, unmanipulated
  price signal rather than being told when to consume more or less.

Both effects are read once per outer loop iteration (not once per house) to avoid hammering either
API every 2 seconds.

## Installation
```shell
docker build -t producer:1.0 --target producer .
docker build -t consumer:1.0 --target consumer .
docker run -e HOST=http://host.docker.internal:8080 producer:1.0
docker run -e HOST=http://host.docker.internal:8080 -e EU_PRICE_API_URL=http://host.docker.internal:8001 consumer:1.0
```

### Environment variables

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `HOST` | both | required | SA-Marketplace base URL |
| `EU_PRICE_API_URL` | consumer | `http://localhost:8001` | eu-power-poc base URL, for demand response |
| `REFERENCE_PRICE_EUR_PER_KWH` | consumer | `0.15` | "normal" price used to center the demand-response factor |
| `SOLAR_TZ` | producer | `Europe/Amsterdam` | timezone the solar curve is computed in |
| `SOLAR_SUNRISE_HOUR` / `SOLAR_SUNSET_HOUR` | producer | `7` / `19` | daylight window for the solar curve |
