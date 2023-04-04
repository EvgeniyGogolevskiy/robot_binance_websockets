from datetime import datetime
import websockets
import asyncio
import json
from binance.client import Client
from config import api, secret
from create_order import buy_order, sell_order
from find_volatily_pairs import analise_volume
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
        self.dollars_for_order = dollars

    async def main(self):
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    if data['k']['x']:
                        try:
                            now_vol_diff = float(data['k']['Q']) / (float(data['k']['q']) - float(data['k']['Q']))
                        except ZeroDivisionError:
                            now_vol_diff = 1
                        if now_vol_diff < 0.2:
                            price_buy = float(data['k']['c'])
                            a = buy_order(self.pair, self.dollars_for_order, price_buy)
                            price_take1 = a['entry_price'] * 1.002
                            price_take2 = a['entry_price'] * 1.012
                            price_stop= a['entry_price'] * 0.99
                            price_for_traling_stop = a['entry_price'] * 1.002
                            logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, {now_vol_diff} < 0.2')
                            position = True
                            breakeven = False
                            flag_take = False
                while position:
                    data = json.loads(await client.recv())
                    if float(data['k']['c']) >= price_take1 and not flag_take:
                        a = sell_order(self.pair, a['amt']/2)
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, ---------TAKE1---------')
                        flag_take = True
                    if float(data['k']['c']) >= price_take2:
                        a = sell_order(self.pair, a['amt'])
                        logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, ---------TAKE_PROFIT---------')
                        position = False
                    if float(data['k']['c']) <= price_stop:
                        sell_order(self.pair, a['amt'])
                        if breakeven:
                            logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _________BREAKEVEN_________')
                        if not breakeven:
                            logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _________STOP_LOSS_________')
                        position = False
                    if price_for_traling_stop <= float(data['k']['c']) < price_take2:
                        if not breakeven:
                            price_stop = a['entry_price']
                            breakeven = True
                        if breakeven:
                            price_stop *= 1.001
                        price_for_traling_stop *= 1.002


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in analise_volume():
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
