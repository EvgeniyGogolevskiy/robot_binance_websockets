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
from calculate_parametrs import calculate_diff_first, calculate_diff
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
        average_volume = statistics.mean(list_volume)
        hight_low = calculate_diff_first(self.data_5m)
        data_rsi = self.data_5m[4][:30].astype(float)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    data_rsi[29] = float(data['k']['c'])
                    sell_vol = float(data['k']['q']) - float(data['k']['Q'])
                    now_vol_diff = float(data['k']['Q']) - (float(data['k']['q']) - float(data['k']['Q']))
                    now_high_low = (float(data['k']['h']) - float(data['k']['l'])) * 100 / float(data['k']['h'])
                    rsi = list(ta.rsi(data_rsi, length=5))[-1]
                    if data['k']['x']:

                        """"""" Расчёт объёма """""""
                        list_volume = list_volume[1:] + [float(data['k']['q'])]
                        average_volume = statistics.mean(list_volume)

                        """"""" Расчёт амплитуды"""""""
                        hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])

                        """"""" Расчёт индикатора RSI """""""
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))

                        await asyncio.sleep(0.5)

                    if average_volume < float(data['k']['q']) < average_volume * 5 and sell_vol < now_vol_diff < float(data['k']['Q']) and hight_low["average_diff"] > 0.15 and rsi < 95:
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        price_take = a['entry_price'] * (1 + hight_low["average_diff"] * 0.01)
                        price_stop= a['entry_price'] * (1 - now_high_low * 0.01)
                        price_for_traling_stop = a['entry_price'] * 1.0025
                        logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, {average_volume * 2.5} < {float(data["k"]["q"])} < {average_volume * 7} and {sell_vol} < {now_vol_diff} < {float(data["k"]["Q"])}, av_diff {round(hight_low["average_diff"], 2)} rsi = {round(rsi, 2)}')
                        position = True
                        breakeven = False
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        list_volume = list_volume[1:] + [float(data['k']['q'])]
                        average_volume = statistics.mean(list_volume)
                        hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, a['amt'])
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, ---------TAKE_PROFIT---------')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        if breakeven:
                            logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _________BREAKEVEN_________')
                        if not breakeven:
                            logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _________STOP_LOSS_________')
                        position = False
                    if price_for_traling_stop <= float(data['k']['c']) < price_take:
                        if not breakeven:
                            price_stop = a['entry_price'] * 1.0015
                            breakeven = True
                        if breakeven:
                            price_stop *= 1.002
                        price_for_traling_stop *= 1.005


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 30)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()