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
        data_klines = calculate_diff_first(self.data_5m)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    MA3 = statistics.mean(data_klines['data_low_ma'][:-1] + [float(data['k']['l'])])
                    if data['k']['x']:

                        """"""" Расчёт волатильности """""""
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_low_ma'])

                        await asyncio.sleep(0.5)

                    if float(data['k']['c']) < MA3*(1 - data_klines['average_diff'] * 0.04):
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            price_breakeven = a['entry_price'] * (1 + data_klines['average_diff'] * 0.01)
                            price_take = max(a['entry_price'] * (1 + data_klines['average_diff'] * 0.03), a['entry_price']*1.008)
                            price_stop= max(a['entry_price'] * (1 - data_klines['average_diff'] * 0.02), a['entry_price']*0.993)
                            position = True
                            breakeven = False
                            avg_ampl1 = data_klines['average_diff']
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_low_ma'])
                    if not breakeven and float(data['k']['c']) >= price_breakeven:
                        price_stop = price_buy * 1.001
                        breakeven = True
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, a['amt'])
                        logger.info(
                            f'take_profit, {str(datetime.now())[8:19]}, {self.pair}, '
                            f'buy= {price_buy}, MA3= {round(MA3, 4)}, avg-ampl= {avg_ampl1},')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        if not breakeven:
                            logger.info(
                                f'stop_loss, {str(datetime.now())[8:19]}, {self.pair}, '
                                f'buy= {price_buy}, MA3= {round(MA3, 4)}, avg-ampl= {avg_ampl1},')
                        else:
                            logger.info(
                                f'breakeven, {str(datetime.now())[8:19]}, {self.pair}, '
                                f'buy= {price_buy}, MA3= {round(MA3,4)}, avg-ampl= {avg_ampl1},')
                        position = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 250)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()