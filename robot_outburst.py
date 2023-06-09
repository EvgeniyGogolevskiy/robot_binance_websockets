from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
from config import api, secret
from calculate_parametrs import calculate_diff_first, calculate_diff, calculate_volume_diff_first, calculate_diff_volume
from create_order import buy_order, sell_order, close_sell_order, close_buy_order
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
        amplituda = data_klines['list_diff'][-1]
        data_volume = calculate_volume_diff_first(self.data_5m)
        volume = data_volume['list_volume'][-1]
        vol_otnosh = data_volume['list_volume_diff'][-1]
        position = False
        flag = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        flag = True
                        maxprice = float(data['k']['h'])
                        minprice = float(data['k']['l'])

                        """"""" Расчёт волатильности """""""
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        amplituda = data_klines['list_diff'][-1]

                        """"""" Расчёт объёма """""""
                        data_volume = calculate_diff_volume(data, data_volume['list_volume'], data_volume['list_volume_diff'])
                        volume = data_volume['list_volume'][-1]
                        vol_otnosh = data_volume['list_volume_diff'][-1]

                    if amplituda > data_klines['average_diff5']*4 > 0.9 and 8 < (volume / data_volume['average_vol']) < 18 and 0.4 < vol_otnosh < 0.9 and flag:
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            price_take = a['entry_price'] * (1 + amplituda * 0.0025)
                            price_stop = max(a['entry_price'] * (1 - amplituda * 0.005), minprice * (1 - amplituda * 0.002), a['entry_price'] * 0.98)
                            position = True
                            side = 'buy'
                            avg_ampl1 = data_klines['average_diff']
                            avg_ampl15 = data_klines['average_diff5']
                            avg_vol1 = data_volume['average_vol']
                            amplituda1 = amplituda
                            volume1 = volume
                            vol_otnosh1 = vol_otnosh
                    elif amplituda > data_klines['average_diff5']*8 > 0.9 and 1.1 < vol_otnosh < 3 and flag:
                        price_buy = float(data['k']['c'])
                        a = sell_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            price_take = a['entry_price'] * (1 - amplituda * 0.0025)
                            price_stop = min(a['entry_price'] * (1 + amplituda * 0.005), maxprice * (1 + amplituda * 0.002), a['entry_price'] * 1.02)
                            position = True
                            side = 'sell'
                            avg_ampl1 = data_klines['average_diff']
                            avg_ampl15 = data_klines['average_diff5']
                            avg_vol1 = data_volume['average_vol']
                            amplituda1 = amplituda
                            volume1 = volume
                            vol_otnosh1 = vol_otnosh
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        data_klines = calculate_diff(data, data_klines['list_diff'], data_klines['data_high_ma'])
                        amplituda = data_klines['list_diff'][-1]
                        data_volume = calculate_diff_volume(data, data_volume['list_volume'], data_volume['list_volume_diff'])
                        volume = data_volume['list_volume'][-1]
                        vol_otnosh = data_volume['list_volume_diff'][-1]
                    if side == 'buy':
                        if float(data['k']['c']) >= price_take:
                            close_buy_order(self.pair, a['amt'])
                            logger.info(
                                f'take_profit {str(datetime.now())[8:19]}, {self.pair}, ampl_otnosh={round(amplituda1 / avg_ampl1, 2)}, '
                                f'vol_otnosh={round(volume1 / avg_vol1, 2)}, vol_buy_sell={round(vol_otnosh1, 2)}, '
                                f'ao5={round(amplituda1 / avg_ampl15, 2)}, avg_ampl={avg_ampl15}')
                            position = False
                            flag = False
                        if float(data['k']['c']) <= price_stop:
                            close_buy_order(self.pair, a['amt'])
                            logger.info(
                                f'stop_loss {str(datetime.now())[8:19]}, {self.pair}, ampl_otnosh={round(amplituda1 / avg_ampl1, 2)}, '
                                f'vol_otnosh={round(volume1 / avg_vol1, 2)}, vol_buy_sell={round(vol_otnosh1, 2)}, '
                                f'ao5={round(amplituda1 / avg_ampl15, 2)}, avg_ampl={avg_ampl15}')
                            position = False
                            flag = False
                    if side == 'sell':
                        if float(data['k']['c']) <= price_take:
                            close_sell_order(self.pair, abs(a['amt']))
                            logger.info(
                                f'take_profit {str(datetime.now())[8:19]}, {self.pair}, ampl_otnosh={round(amplituda1 / avg_ampl1, 2)}, '
                                f'vol_otnosh={round(volume1 / avg_vol1, 2)}, vol_buy_sell={round(vol_otnosh1, 2)}, '
                                f'ao5={round(amplituda1 / avg_ampl15, 2)}, avg_ampl={avg_ampl15}')
                            position = False
                            flag = False
                        if float(data['k']['c']) >= price_stop:
                            close_sell_order(self.pair, abs(a['amt']))
                            logger.info(
                                f'stop_loss {str(datetime.now())[8:19]}, {self.pair}, ampl_otnosh={round(amplituda1 / avg_ampl1, 2)}, '
                                f'vol_otnosh={round(volume1 / avg_vol1, 2)}, vol_buy_sell={round(vol_otnosh1, 2)}, '
                                f'ao5={round(amplituda1 / avg_ampl15, 2)}, avg_ampl={avg_ampl15}')
                            position = False
                            flag = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 10)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()
