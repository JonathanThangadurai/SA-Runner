from __future__ import annotations

import math
import os
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

host = os.environ['HOST']

# Daylight window and timezone for the solar production curve - NL, where
# eu-power-poc's price data comes from. Rough October daylight hours; houses
# produce nothing outside this window, same as real solar panels at night.
SOLAR_TZ = ZoneInfo(os.environ.get('SOLAR_TZ', 'Europe/Amsterdam'))
SUNRISE_HOUR = float(os.environ.get('SOLAR_SUNRISE_HOUR', '7'))
SUNSET_HOUR = float(os.environ.get('SOLAR_SUNSET_HOUR', '19'))


def solar_factor(now: datetime | None = None) -> float:
    """0 at night, peaking at 1 at solar noon (midpoint of the daylight window).

    This is what makes the simulation's economics line up with the real NL
    price curve: both dip around midday (real solar oversupply lowers the
    real price; synthetic solar surplus here makes community trades cheap)
    and both are expensive in the evening, without either side being told
    about the other.
    """
    now = now or datetime.now(SOLAR_TZ)
    hour = now.hour + now.minute / 60
    if hour <= SUNRISE_HOUR or hour >= SUNSET_HOUR:
        return 0.0
    fraction = (hour - SUNRISE_HOUR) / (SUNSET_HOUR - SUNRISE_HOUR)
    return math.sin(math.pi * fraction) ** 2


time.sleep(10)

while True:
    factor = solar_factor()
    for community in range(1, 10):
        for house in range(1, 5):
            production = random.uniform(2, 10) * factor
            payload = {"communityId": community, "houseId": house, "energyProduced": production}
            response = requests.post(url=f'{host}/api/v1/productions', json=payload)
            print(f'Produced {production:.2f} (solar factor {factor:.2f}) for community: {community}, house: {house}')
    time.sleep(2)
