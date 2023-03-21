import statistics
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
import pandas_ta as ta
from config import api, secret
from create_order import buy_order, sell_order
from find_volatily_pairs import top_volatily
import logging
import sys
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

CLIENT = Client(api, secret)
logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger('mylogger')
logger.setLevel(logging.INFO)


class Strategy:
    def __init__(self, pair, interval, q, depo):
        self.pair = pair
        self.interval = interval
        self.vol_median = q
        self.vol_max = q
        self.vol0 = 0
        self.data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=30))
        self.average_diff = 0
        self.depo = depo

    async def main(self):
        data_5m_volume_buy = list(self.data_5m[10][19:29])
        data_5m_hight = list(self.data_5m[2][19:29])
        data_5m_low = list(self.data_5m[3][19:29])
        data_rsi = self.data_5m[4][:30].astype(float)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    self.vol0 = float(data['k']['q']) * 3
                    data_rsi[29] = float(data['k']['c'])
                    rsi = list(ta.rsi(data_rsi, length=2))[-1]
                    if data['k']['x']:
                        data_5m_volume_buy = data_5m_volume_buy[1:] + [data['k']['Q']]

                        data_5m_hight = data_5m_hight[1:] + [float(data['k']['h'])]
                        data_5m_low = data_5m_low[1:] + [float(data['k']['l'])]
                        list_diff = []
                        for i in range(len(data_5m_hight)):
                            list_diff.append(float(data_5m_hight[i]) - float(data_5m_low[i]) * 100 / float(data_5m_hight[i]))
                        self.average_diff = statistics.mean(list_diff)
                        min10 = min(data_5m_low)

                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))

                        # logger.info(event_time, '  ', self.pair, '  ', data_rsi, rsi)
                    if float(data_5m_volume_buy[7]) < float(data_5m_volume_buy[8]) < float(data_5m_volume_buy[9]) < float(data['k']['Q']):
                        price_buy = float(data['k']['c'])
                        buy_order(self.pair, self.depo, price_buy)
                        price_take = price_buy * 1.01
                        price_stop = min10 * 0.998
                        logger.info(f'{datetime.now()}, {self.pair} цена = {data["k"]["c"]}, объём {self.vol_median} < {self.vol0} < {float(data["k"]["Q"])} ({round(float(data["k"]["Q"]) / self.vol0, 3)}), average_diff {round(self.average_diff, 2)} rsi = {round(rsi, 2)}')
                        position = True
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_5m_volume_buy = data_5m_volume_buy[1:] + [data['k']['Q']]
                        data_5m_hight = data_5m_hight[1:] + [float(data['k']['h'])]
                        data_5m_low = data_5m_low[1:] + [float(data['k']['l'])]
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, self.depo, price_buy)
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, "---------------TAKE_PROFIT---------------")')
                        position = False
                        self.vol_median = 1000000000
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, self.depo, price_buy)
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, "_______________STOP_LOSS_______________" ')
                        position = False
                        self.vol_median = 1000000000


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 1000000000, 50)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()
