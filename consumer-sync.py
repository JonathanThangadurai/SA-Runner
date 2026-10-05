from __future__ import annotations

import os
import random
import time

import requests

host = os.environ['HOST']

# eu-power-poc (github.com/JonathanThangadurai/eu-power-poc) - the live NL
# day-ahead price feed, called directly here (not through the Marketplace)
# so demand response runs off the same real signal the Marketplace prices
# trades against.
EU_PRICE_API_URL = os.environ.get('EU_PRICE_API_URL', 'http://localhost:8001')
REFERENCE_PRICE_EUR_PER_KWH = float(os.environ.get('REFERENCE_PRICE_EUR_PER_KWH', '0.15'))
MIN_DEMAND_FACTOR = 0.3
MAX_DEMAND_FACTOR = 2.0


def demand_factor() -> float:
    """>1 when the real price is cheap (consume more - shift demand to cheap hours),
    <1 when it's expensive (consume less - defer demand), clamped to a sane range so
    a price near zero or missing data never zeroes out or explodes consumption.

    This is what demand response actually means: pull EnergyZero's current price
    directly (the same source the Marketplace charges against) and let consumption
    volume react to it, instead of consuming the same random amount regardless of
    whether power happens to be cheap or expensive right now.
    """
    try:
        resp = requests.get(f'{EU_PRICE_API_URL}/price/current', timeout=5)
        resp.raise_for_status()
        price = resp.json()['price_excl_vat_eur_per_kwh']
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f'Could not reach EU price API at {EU_PRICE_API_URL}, no demand adjustment: {exc}')
        return 1.0

    factor = REFERENCE_PRICE_EUR_PER_KWH / max(price, 0.01)
    return max(MIN_DEMAND_FACTOR, min(MAX_DEMAND_FACTOR, factor))


time.sleep(10)

while True:
    factor = demand_factor()
    for community in range(1, 10):
        for house in range(1, 5):
            consumption = random.uniform(2, 10) * factor
            payload = {"communityId": community, "houseId": house, "energyNeed": consumption}
            response = requests.post(url=f'{host}/api/v1/consumptions', json=payload)
            print(f'Consume {consumption:.2f} (demand factor {factor:.2f}) for community: {community}, house: {house} was {response.text}')
    time.sleep(2)
