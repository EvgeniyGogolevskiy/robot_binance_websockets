import time
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd

pair = 'MINAUSDT'
interval = '1m'

CLIENT = Client()


async def main():
    position = False
    q = 1000000000
    url = f'wss://fstream.binance.com/ws/{pair.lower()}@kline_{interval}'
    async with websockets.connect(url) as client:
        while True:
            while not position:
                data = json.loads(await client.recv())
                event_time = datetime.fromtimestamp(data['E'] // 1000)
                if data['k']['x']:
                    data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=pair, interval='1m', limit=5))
                    vol1 = float(data_5m.values[1][10])
                    vol2 = float(data_5m.values[2][10])
                    vol3 = float(data_5m.values[3][10])
                    vol4 = float(data_5m.values[4][10])
                    q = vol1 + vol2 + vol3 + vol4
                    print(event_time, '  ', data['k']['Q'], '  ', q)
                if float(data['k']['Q']) > q:
                    price_buy = float(data['k']['c'])
                    price_take = price_buy*1.005
                    price_stop = price_buy*0.995
                    print(f'{event_time}, цена = {data["k"]["c"]}, объём {data["k"]["Q"]} > {q}')
                    position = True
            while position:
                data = json.loads(await client.recv())
                if float(data['k']['c']) >= price_take:
                    print('take_profit', data['k']['c'])
                    position = False
                    while not data['k']['x']:
                        time.sleep(0.1)
                if float(data['k']['c']) <= price_stop:
                    print('stop_loss', data['k']['c'])
                    position = False
                    while not data['k']['x']:
                        time.sleep(0.1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
