import asyncio
import datetime

import pandas as pd

from binance import AsyncClient, BinanceSocketManager, Client

cl = Client()


class AlertDownPrice:
    def __init__(self, pair):
        self.pair = pair
        self.price_now = float(cl.futures_mark_price(symbol=self.pair)['markPrice'])
        self.max_price_per_hour = float(
            pd.DataFrame(cl.futures_klines(symbol=self.pair, interval='1m', limit=60)).max()[2])

    async def getPrice(self):
        client = await AsyncClient.create()
        bm = BinanceSocketManager(client)
        ts = bm.aggtrade_futures_socket(self.pair)
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                self.price_now = float(res['data']['p'])
        await client.close_connection()

    async def nested(self):
        return 0

    async def calculate(self):
        max_price = 0
        price_low = self.price_now*2
        while True:
            await self.nested()
            time_now = datetime.datetime.now()
            if time_now.second % 5 == 0:
                self.max_price_per_hour = float(
                    pd.DataFrame(cl.futures_klines(symbol=self.pair, interval='1m', limit=60)).max()[2])
                if max_price != self.max_price_per_hour:
                    print(f'Максимальная цена за последний час {self.max_price_per_hour}')
                    max_price = self.max_price_per_hour
            if self.price_now <= self.max_price_per_hour * 0.99 and self.price_now < price_low:
                print(
                    f'Цена ({self.price_now}) ниже на 1% или более, чем максимальная за последний час ({self.max_price_per_hour})')
                price_low = self.price_now

    async def start(self):
        task1 = asyncio.create_task(
            self.getPrice())
        task2 = asyncio.create_task(
            self.calculate())
        await task1
        await task2


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    adp = AlertDownPrice("AGIXBUSD")
    try:
        asyncio.ensure_future(adp.start())
        print("start")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        print('Finished!')
        loop.close()
