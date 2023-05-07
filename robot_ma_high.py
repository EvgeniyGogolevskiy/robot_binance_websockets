import statistics
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
import pandas_ta as ta
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
        self.data_5m = pd.DataFrame(CLIENT.futures_klines(symbol=self.pair, interval=self.interval, limit=300))
        self.dollars_for_order = dollars

    async def main(self):
        data_klines = calculate_diff_first(self.data_5m)
        MA2 = statistics.mean(data_klines['data_high_ma'])
        data_rsi = self.data_5m[3][:300].astype(float)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:

                        """"""" Расчёт волатильности и скользящей средней """""""
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        MA2 = statistics.mean(data_klines['data_high_ma'])

                        """"""" Расчёт индикатора RSI """""""
                        data_rsi = data_rsi[1:299].append(pd.Series([float(data['k']['c'])]))
                        rsi = list(ta.rsi(data_rsi, length=10))[-1]

                    if float(data['k']['o']) <= float(data['k']['c']) < MA2*(1 - data_klines['average_diff'] * 0.02) and data_klines['average_diff'] > 0.19 and rsi < 15:
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            price_take1 = a['entry_price'] * (1 + data_klines['average_diff'] * 0.015)
                            price_take2 = a['entry_price'] * (1 + data_klines['average_diff'] * 0.03)
                            price_take3 = a['entry_price'] * (1 + data_klines['average_diff'] * 0.06)
                            price_stop= min(a['entry_price'] * (1 - data_klines['average_diff'] * 0.02), a['entry_price']*0.99)
                            position = True
                            take1 = False
                            take2 = False
                            avg_ampl1 = data_klines['average_diff']
                            MA = MA2
                            rsi10 = rsi
                            porog = (MA*(1-avg_ampl1*0.02) - price_buy) * 100 / MA*(1-avg_ampl1*0.02)
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        MA2 = statistics.mean(data_klines['data_high_ma'])
                        data_rsi = data_rsi[1:299].append(pd.Series([float(data['k']['c'])]))
                        rsi = list(ta.rsi(data_rsi, length=10))[-1]
                    if price_take1 <= float(data['k']['c']) < price_take2 and not take1:
                        a = sell_order(self.pair, a['amt']//3)
                        take1 = True
                    if price_take2 <= float(data['k']['c']) < price_take3 and not take2:
                        a = sell_order(self.pair, a['amt']//2)
                        take2 = True
                    if float(data['k']['c']) >= price_take3:
                        sell_order(self.pair, a['amt'])
                        logger.info(
                            f'take_profit, {str(datetime.now())[8:19]}, {self.pair}, buy= {price_buy}, '
                            f'MA2= {round(MA, 4)}, avg-ampl= {avg_ampl1}, rsi={rsi10}, porog= {round(porog, 4)}')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        logger.info(
                            f'stop_loss and take1={take1} and take2={take2}, {str(datetime.now())[8:19]}, {self.pair}, buy= {price_buy}, '
                            f'MA2= {round(MA, 4)}, avg-ampl= {avg_ampl1}, rsi={rsi10}, porog= {round(porog, 4)}')
                        position = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 100)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()