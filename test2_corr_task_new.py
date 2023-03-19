from datetime import datetime
import websockets
import asyncio
import json
from scipy.stats import pearsonr
from binance.client import Client

CLIENT = Client()


class DiffPrice:
    def __init__(self, pair):
        self.pair: str = pair
        self.list_eth: list[float] = []
        self.list_btc: list[float] = []

    async def priceBTC(self):
        url = f'wss://fstream.binance.com/ws/btcusdt@kline_1m'
        async with websockets.connect(url) as client:
            while True:
                data = json.loads(await client.recv())
                if len(self.list_btc) == 14400:
                    self.list_btc = self.list_btc[1:] + [float(data['k']['c'])]
                else:
                    self.list_btc.append(float(data['k']['c']))

    async def priceETH(self):
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_1m'
        async with websockets.connect(url) as client:
            while True:
                data = json.loads(await client.recv())
                if len(self.list_eth) == 14400:
                    self.list_eth = self.list_eth[1:] + [float(data['k']['c'])]
                    coef = pearsonr(self.list_btc, self.list_eth)[0]
                    diff_eth = (self.list_eth[-1] - self.list_eth[0]) * 100 / self.list_eth[-1]
                    diff_only_eth = diff_eth * (1 - coef)
                    if abs(diff_eth) >= 1:
                        print(f'Движение ETHUSDT по рынку за час {diff_eth}, С учётом корреляции с биткоином {diff_only_eth}')
                else:
                    self.list_eth.append(float(data['k']['c']))

    async def main(self):
        task1 = asyncio.create_task(self.priceBTC())
        task2 = asyncio.create_task(self.priceETH())

        await task1
        await task2


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    ad = DiffPrice("ETHUSDT")
    try:
        asyncio.ensure_future(ad.main())
        print("start", datetime.now())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        print('Finished!')
        loop.close()
