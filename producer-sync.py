from __future__ import annotations

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from real_data import real_value_kwh

host = os.environ['HOST']

# NL, where eu-power-poc's price data comes from - the timezone the real
# Ausgrid household data is replayed against (see real_data.py for the
# season-shift that aligns Sydney's seasonal cycle with the Northern
# Hemisphere's, so "NL summer" plays back a real Sydney summer day).
SOLAR_TZ = ZoneInfo(os.environ.get('SOLAR_TZ', 'Europe/Amsterdam'))

time.sleep(10)

while True:
    now = datetime.now(SOLAR_TZ)
    for community in range(1, 10):
        for house in range(1, 5):
            production = real_value_kwh(community, house, "GG", now)
            payload = {"communityId": community, "houseId": house, "energyProduced": production}
            response = requests.post(url=f'{host}/api/v1/productions', json=payload)
            print(
                f'Produced {production:.3f} kWh (real Ausgrid data) '
                f'for community: {community}, house: {house}'
            )
    time.sleep(2)
