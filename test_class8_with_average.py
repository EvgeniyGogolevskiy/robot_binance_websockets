import statistics
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
import pandas_ta as ta
from config import api, secret
from create_order import buy_order, sell_order, buy_order_average, sell_order_average
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
        self.q = q
        self.q_max = q
        self.vol0 = 0
        self.data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=30))
        self.average_diff = 0
        self.depo = depo

    async def main(self):
        data_5m_volume_buy = list(self.data_5m[10][19:29])
        data_5m_volume = list(self.data_5m[7][19:29])
        data_5m_hight = list(self.data_5m[2][24:29])
        data_5m_low = list(self.data_5m[3][24:29])
        data_rsi = self.data_5m[4][:30].astype(float)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    self.vol0 = (float(data['k']['q']) - float(data['k']['Q'])) * 3
                    data_rsi[29] = float(data['k']['c'])
                    rsi = list(ta.rsi(data_rsi, length=2))[-1]
                    if data['k']['x']:
                        data_5m_volume_buy = data_5m_volume_buy[1:] + [data['k']['Q']]
                        data_5m_volume = data_5m_volume[1:] + [data['k']['q']]
                        vol1 = float(data_5m_volume[0]) - float(data_5m_volume_buy[0])
                        vol2 = float(data_5m_volume[1]) - float(data_5m_volume_buy[1])
                        vol3 = float(data_5m_volume[2]) - float(data_5m_volume_buy[2])
                        vol4 = float(data_5m_volume[3]) - float(data_5m_volume_buy[3])
                        vol5 = float(data_5m_volume[4]) - float(data_5m_volume_buy[4])
                        vol6 = float(data_5m_volume[5]) - float(data_5m_volume_buy[5])
                        vol7 = float(data_5m_volume[6]) - float(data_5m_volume_buy[6])
                        vol8 = float(data_5m_volume[7]) - float(data_5m_volume_buy[7])
                        vol9 = float(data_5m_volume[8]) - float(data_5m_volume_buy[8])
                        vol10 = float(data_5m_volume[9]) - float(data_5m_volume_buy[9])
                        list_vol = [vol1, vol2, vol3, vol4, vol5, vol6, vol7, vol8, vol9, vol10]
                        self.q_max = max(list_vol)
                        self.q = statistics.mean(list_vol) * 2.5

                        data_5m_hight = data_5m_hight[1:] + [float(data['k']['h'])]
                        data_5m_low = data_5m_low[1:] + [float(data['k']['l'])]
                        diff1 = round(((float(data_5m_hight[0]) - float(data_5m_low[0])) * 100 / float(data_5m_hight[0])), 3)
                        diff2 = round(((float(data_5m_hight[1]) - float(data_5m_low[1])) * 100 / float(data_5m_hight[1])), 3)
                        diff3 = round(((float(data_5m_hight[2]) - float(data_5m_low[2])) * 100 / float(data_5m_hight[2])), 3)
                        diff4 = round(((float(data_5m_hight[3]) - float(data_5m_low[3])) * 100 / float(data_5m_hight[3])), 3)
                        diff5 = round(((float(data_5m_hight[4]) - float(data_5m_low[4])) * 100 / float(data_5m_hight[4])), 3)
                        self.average_diff = (diff1 + diff2 + diff3 + diff4 + diff5) / 5

                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))

                        # logger.info(event_time, '  ', self.pair, '  ', data_rsi, rsi)
                    if self.q < self.vol0 < float(data['k']['Q']) and self.q_max < float(data['k']['Q']) and self.average_diff > 0.15 and rsi < 40:
                        price_buy = float(data['k']['c'])
                        buy_order(self.pair, self.depo, price_buy)
                        price_take = price_buy * 1.0075
                        price_average = price_buy * 0.993
                        price_stop = price_average * 0.993
                        logger.info(f'{datetime.now()}, {self.pair} цена = {data["k"]["c"]}, объём {self.q} < {self.vol0} < {float(data["k"]["Q"])} ({round(float(data["k"]["Q"]) / self.vol0, 3)}), average_diff {round(self.average_diff, 2)} rsi = {round(rsi, 2)}')
                        position = True
                        flag_average = False
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_5m_volume_buy = data_5m_volume_buy[1:] + [data['k']['Q']]
                        data_5m_volume = data_5m_volume[1:] + [data['k']['q']]
                        data_5m_hight = data_5m_hight[1:] + [float(data['k']['h'])]
                        data_5m_low = data_5m_low[1:] + [float(data['k']['l'])]
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                    if float(data['k']['c']) >= price_take:
                        if not flag_average:
                            sell_order(self.pair, self.depo, price_buy)
                        if flag_average:
                            sell_order_average(self.pair, self.depo, price_buy)
                        logger.info(f'{datetime.now()}, {self.pair}, TAKE_PROFIT, {data["k"]["c"]}')
                        position = False
                        self.q = 1000000000
                    if price_stop < float(data['k']['c']) <= price_average and not flag_average:
                        buy_order_average(self.pair, self.depo, price_buy)
                        logger.info(f'{self.pair}, AVERAGE, {data["k"]["c"]}, {datetime.now()}')
                        price_take = (float(data['k']['c']) + price_buy) / 2 * 1.0045
                        flag_average = True
                    if float(data['k']['c']) <= price_stop:
                        sell_order_average(self.pair, self.depo, price_buy)
                        logger.info(f'{self.pair}, STOP_LOSS, {data["k"]["c"]}, {datetime.now()}')
                        position = False
                        self.q = 1000000000


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
