from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
import pandas as pd
from config import api, secret
from create_order import buy_order, sell_order
from find_volatily_pairs import top_volatily
from calculate_parametrs import calculate_volume_diff_first, calculate_diff_volume
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
        list_volume_diff = calculate_volume_diff_first(self.data_5m)
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    seconds = int(str(datetime.now().second))
                    if seconds > 30:
                        data = json.loads(await client.recv())
                        if data['k']['x']:

                            list_volume_diff = calculate_diff_volume(data, list_volume_diff, self.pair)

                            await asyncio.sleep(0.5)

                        if list_volume_diff[-2] > 1 and list_volume_diff[-1] > 3:
                            price_buy = float(data['k']['c'])
                            a = buy_order(self.pair, self.dollars_for_order, price_buy)
                            price_take = a['entry_price'] * 1.01
                            price_stop= a['entry_price'] * 0.99
                            price_for_traling_stop = a['entry_price'] * 1.003
                            logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, {list_volume_diff[-2]}, {list_volume_diff[-1]}')
                            position = True
                            breakeven = False
                while position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        list_volume_diff = calculate_diff_volume(data, list_volume_diff, self.pair)
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