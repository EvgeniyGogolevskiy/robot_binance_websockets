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
from calculate_parametrs import calculate_volume_first, calculate_volume, calculate_diff_first, calculate_diff
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
        self.data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=30))
        self.depo = depo

    async def main(self):
        list_volume_diff = calculate_volume_first(self.data_5m)
        hight_low = calculate_diff_first(self.data_5m)
        data_rsi = self.data_5m[4][:30].astype(float)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    data_rsi[29] = float(data['k']['c'])
                    now_vol_diff = float(data['k']['Q']) - (float(data['k']['q']) - float(data['k']['Q']))
                    rsi = list(ta.rsi(data_rsi, length=2))[-1]
                    if data['k']['x']:

                        """"""" Расчёт объёма """""""
                        list_volume_diff = calculate_volume(data, list_volume_diff)

                        """"""" Расчёт амплитуды"""""""
                        hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])

                        """"""" Расчёт индикатора RSI """""""
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))

                        await asyncio.sleep(0.5)
                        # logger.info(event_time, '  ', self.pair, '  ', data_rsi, rsi)
                    if  0 < list_volume_diff[-1] * 2.5 < (float(data['k']['q']) - float(data['k']['Q'])) * 2.5 < now_vol_diff and rsi < 60:
                        price_buy = float(data['k']['c'])
                        buy_order(self.pair, self.depo, price_buy)
                        price_take = price_buy * (1 + hight_low["average_diff"] * 0.05)
                        price_stop = price_buy * (1 - hight_low["average_diff"] * 0.01)
                        #price_stop = min(hight_low['min10'] * 0.998, price_buy * 0.994)
                        logger.info(f'{datetime.now()}, {self.pair} цена = {data["k"]["c"]}, ({now_vol_diff / (float(data["k"]["q"]) - float(data["k"]["Q"]))}), average_diff {round(hight_low["average_diff"], 2)} rsi = {round(rsi, 2)}')
                        position = True
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        list_volume_diff = calculate_volume(data, list_volume_diff)
                        hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, self.depo, price_buy)
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, "---------------TAKE_PROFIT---------------")')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, self.depo, price_buy)
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, "_______________STOP_LOSS_______________" ')
                        position = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '5m', 1000000000, 20)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()
