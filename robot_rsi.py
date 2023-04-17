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
        data_rsi = self.data_5m[4][:30].astype(float)
        rsi12_last = list(ta.rsi(data_rsi, length=12))[-1]
        rsi24_last = list(ta.rsi(data_rsi, length=24))[-1]
        position = False
        url = f'wss://fstream.binance.com/ws/{self.pair.lower()}@kline_{self.interval}'
        async with websockets.connect(url) as client:
            while True:
                while not position:
                    data = json.loads(await client.recv())
                    data_rsi[29] = float(data['k']['c'])
                    rsi12 = list(ta.rsi(data_rsi, length=12))[-1]
                    rsi24 = list(ta.rsi(data_rsi, length=24))[-1]
                    if data['k']['x']:

                        """"""" Расчёт индикатора RSI """""""
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                        rsi12_last = list(ta.rsi(data_rsi, length=12))[-1]
                        rsi24_last = list(ta.rsi(data_rsi, length=24))[-1]

                        await asyncio.sleep(0.5)

                    if rsi12_last < 30 and rsi12_last < rsi24_last and rsi12 > rsi24:
                        price_buy = float(data['k']['c'])
                        a = buy_order(self.pair, self.dollars_for_order, price_buy)
                        if a['position']:
                            logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, rsi_last= {rsi12_last}, rsi= {rsi12}')
                            position = True
                while position:
                    data = json.loads(await client.recv())
                    rsi12 = list(ta.rsi(data_rsi, length=12))[-1]
                    rsi24 = list(ta.rsi(data_rsi, length=24))[-1]
                    if data['k']['x']:
                        data_rsi[29] = float(data['k']['c'])
                        data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                    if rsi12 < rsi24*0.85:
                        sell_order(self.pair, a['amt'])
                        logger.info(f'{str(datetime.now())[8:19]}, {self.pair}, {data["k"]["c"]}, pnl= {(float(data["k"]["c"]) - price_buy) * 100 / float(data["k"]["c"])}')
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