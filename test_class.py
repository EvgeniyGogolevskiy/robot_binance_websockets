import time
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd

CLIENT = Client()


class Strategy:
    def __init__(self, pair, interval, q):
        self.pair = pair
        self.interval = interval
        self.q = q
        self.data_5m = list(pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=5))[10][:5])

    async def main(self):
        dollars_profit = 0
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    event_time = datetime.fromtimestamp(data['E'] // 1000)
                    if data['k']['x']:
                        self.data_5m = self.data_5m[1:] + [data['k']['Q']]
                        vol1 = float(self.data_5m[0])
                        vol2 = float(self.data_5m[1])
                        vol3 = float(self.data_5m[2])
                        vol4 = float(self.data_5m[3])
                        vol5 = float(self.data_5m[4])
                        self.q = vol1 + vol2 + vol3 + vol4 + vol5
                        # print(event_time, '  ', self.pair, '  ', data['k']['Q'], '  ', self.q)
                    if float(data['k']['Q']) > self.q:
                        price_buy = float(data['k']['c'])
                        price_take = price_buy * 1.02
                        price_stop = price_buy * 0.99
                        print(f'{event_time}, {self.pair} цена = {data["k"]["c"]}, объём {data["k"]["Q"]} > {self.q}')
                        position = True
                while position:
                    data = json.loads(await client.recv())
                    if float(data['k']['c']) >= price_take:
                        print(self.pair, 'take_profit', data['k']['c'], datetime.now())
                        position = False
                        dollars_profit += 1.9
                        print(f'прибыль {dollars_profit}')
                    if float(data['k']['c']) <= price_stop:
                        print(self.pair,'stop_loss', data['k']['c'], datetime.now())
                        position = False
                        dollars_profit -= 1.1
                        print(f'прибыль {dollars_profit}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    all_pairs = pd.DataFrame(CLIENT.futures_exchange_info()['symbols'])[['pair', 'quoteAsset']]
    pairs = all_pairs.pair.dropna().unique()[6:46]
    try:
        for pair in pairs:
            adp = Strategy(pair, '1m', 1000000000)
            asyncio.ensure_future(adp.main())
        print("start")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        print('Finished!')
        loop.close()
