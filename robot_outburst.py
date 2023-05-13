import statistics
from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
import pandas_ta as ta
from config import api, secret
from calculate_parametrs import calculate_diff_first, calculate_diff, calculate_volume_diff_first, calculate_diff_volume
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
        data_volume = calculate_volume_diff_first(self.data_5m)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:

                        """"""" Расчёт волатильности """""""
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        amplituda = data_klines['list_diff'][-1]

                        """"""" Расчёт объёма """""""
                        data_volume = calculate_diff_volume(data, data_volume['list_volume'], data_volume['list_volume_diff'])
                        volume = data_volume['list_volume'][-1]
                        avg_volume = statistics.mean(data_volume['list_volume'])

                    if amplituda > data_klines['average_diff']*5 and float(data['k']['o']) > float(data['k']['c'])*1.001:
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            price_take = a['entry_price'] * 1.001
                            price_stop= a['entry_price'] * 0.999
                            position = True
                            avg_ampl1 = data_klines['average_diff']
                            avg_vol1 = avg_volume
                            amplituda1 = amplituda
                            volume1 = volume
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        amplituda = data_klines['list_diff'][-1]
                        data_volume = calculate_diff_volume(data, data_volume['list_volume'], data_volume['list_volume_diff'])
                        volume = data_volume['list_volume'][-1]
                        avg_volume = statistics.mean(data_volume['list_volume'])
                    if float(data['k']['c']) >= price_take:
                        sell_order(self.pair, a['amt'])
                        logger.info(
                            f'take_profit, {str(datetime.now())[8:19]}, {self.pair}, buy= {price_buy}, '
                            f'amplituda= {amplituda1}, avg-ampl= {avg_ampl1}, volume={volume1}, avg-vol= {avg_vol1}')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        logger.info(
                            f'stop_loss, {str(datetime.now())[8:19]}, {self.pair}, buy= {price_buy}, '
                            f'amplituda= {amplituda1}, avg-ampl= {avg_ampl1}, volume={volume1}, avg-vol= {avg_vol1}')
                        position = False

                        """"""" СДЕЛАТЬ ТАК ЧТОБ АМПЛИТУДА И ОБЪЁМ ПОСЛЕДНЕЙ СВЕЧИ НЕ ВХОДИЛИ В РАСЧЕТ СРЕДНИХ """""""


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