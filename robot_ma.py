import statistics
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
from config import api, secret
from calculate_parametrs import calculate_diff_first, calculate_diff
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
    def __init__(self, pair, interval, dollars):
        self.pair = pair
        self.interval = interval
        self.data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=30))
        self.dollars_for_order = dollars

    async def main(self):
        list_volume = list(map(float, self.data_5m[7][19:29]))
        average_volume = statistics.median(list_volume)
        data_klines = calculate_diff_first(self.data_5m)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    try:
                        now_vol_diff = round(float(data['k']['Q']) / (float(data['k']['q']) - float(data['k']['Q'])),2)
                    except ZeroDivisionError:
                        now_vol_diff = 1
                    now_high_low = round((float(data['k']['h']) - float(data['k']['l'])) * 100 / float(data['k']['h']),2)
                    MA18 = statistics.mean(data_klines['data_close'][:-1] + [float(data['k']['c'])])
                    if data['k']['x']:

                        """"""" Расчёт объёма """""""
                        list_volume = list_volume[1:] + [float(data['k']['q'])]
                        average_volume = statistics.median(list_volume)

                        """"""" Расчёт волатильности """""""
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_close'])

                        await asyncio.sleep(0.5)

                        if average_volume*2 < float(data['k']['q']) and float(data['k']['o'] < MA18 < float(data['k']['q'])):
                            price_buy = float(data['k']['c'])
                            a = buy_order(self.pair, self.dollars_for_order, price_buy)
                            if a['position']:
                                price_take = a['entry_price'] * (1 + now_high_low * 0.01)
                                price_stop= a['entry_price'] * (1 - now_high_low * 0.004)
                                logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, vol/avg-vol= {round(float(data["k"]["q"]) / average_volume, 2)},'
                                            f'ampl= {now_high_low}, avg-ampl= {data_klines["average_diff"]}, vol_otnosh= {now_vol_diff},'
                                            f'MA18= {MA18},')
                                position = True
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        list_volume = list_volume[1:] + [float(data['k']['q'])]
                        average_volume = statistics.median(list_volume)
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_close'])
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, a['amt'])
                        logger.info(f'{str(datetime.now())[8:19]}, {self.pair}, {data["k"]["c"]}, ---------TAKE_PROFIT---------')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        logger.info(f'{str(datetime.now())[8:19]}, {self.pair}, {data["k"]["c"]}, _________STOP_LOSS_________')
                        position = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 200)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()