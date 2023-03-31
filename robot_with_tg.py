import statistics
from datetime import datetime
import websockets
import asyncio
import json
import telebot
from binance.client import Client
import pandas as pd
import pandas_ta as ta
from config import api, secret, tg_bot, my_id_tg
from create_order import buy_order, sell_order
from find_volatily_pairs import top_volatily
from calculate_parametrs import calculate_diff_first, calculate_diff
import logging
import sys
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

CLIENT = Client(api, secret)
bot = telebot.TeleBot(tg_bot)
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
        while True:
            try:
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
                            now_vol_diff = float(data['k']['Q']) - (float(data['k']['q']) - float(data['k']['Q']))
                            rsi = list(ta.rsi(data_rsi, length=2))[-1]
                            if data['k']['x']:

                                """"""" Расчёт объёма """""""
                                list_volume = list_volume[1:] + [float(data['k']['q'])]
                                average_volume = statistics.mean(list_volume)

                                """"""" Расчёт амплитуды"""""""
                                hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])

                                """"""" Расчёт индикатора RSI """""""
                                data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))

                                await asyncio.sleep(0.5)

                            if float(data['k']['q']) > average_volume * 4 and now_vol_diff < float(data['k']['Q']) * -4 and hight_low["average_diff"] > 0.15 and rsi < 1:
                                price_buy = float(data['k']['c'])
                                a = buy_order(self.pair, self.dollars_for_order, price_buy)
                                price_take = a['entry_price'] * 1.02
                                price_stop= a['entry_price'] * (1 - hight_low["average_diff"] * 0.04)
                                price_average = a['entry_price'] * (1 - hight_low["average_diff"] * 0.02)
                                price_for_traling_stop = a['entry_price'] * 1.004
                                logger.info(f'{str(datetime.now())[8:19]}, {self.pair} цена {data["k"]["c"]}, {round(float(data["k"]["q"]), 1)} > {round(average_volume * 4, 1)} and {round(now_vol_diff, 1)} < {round(float(data["k"]["Q"]) * -4, 1)}, av_diff {round(hight_low["average_diff"], 2)} rsi = {round(rsi, 2)}')
                                try:
                                    bot.send_message(my_id_tg, f"Открылась позиция по паре - {self.pair}")
                                except Exception:
                                    logger.info(f'Не отправилось сообщение об открытии сделки по паре {self.pair}')
                                position = True
                                breakeven = False
                                average = False
                        while position:
                            data = json.loads(await client.recv())
                            if data['k']['x']:
                                list_volume = list_volume[1:] + [float(data['k']['q'])]
                                average_volume = statistics.mean(list_volume)
                                hight_low = calculate_diff(data, hight_low['list_diff'], hight_low['data_5m_low'])
                                data_rsi = data_rsi[1:29].append(pd.Series([float(data['k']['c'])]))
                            if float(data['k']['c']) >= price_take:
                                sell_order(self.pair, a['amt'])
                                logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, ---------------TAKE_PROFIT---------------)')
                                position = False
                                try:
                                    bot.send_message(my_id_tg, f"Тейк-профит по паре - {self.pair}")
                                except Exception:
                                    logger.info(f'Не отправилось сообщение о тейке по паре {self.pair}')
                            if float(data['k']['c']) <= price_stop:
                                sell_order(self.pair, a['amt'])
                                logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _________STOP_LOSS - безубыток {breakeven}_________ ')
                                position = False
                                try:
                                    bot.send_message(my_id_tg, f"Стоп-лосс по паре - {self.pair}")
                                except Exception:
                                    logger.info(f'Не отправилось сообщение о стопе по паре {self.pair}')
                            if price_for_traling_stop <= float(data['k']['c']) < price_take:
                                if not breakeven:
                                    price_stop = a['entry_price'] * 1.001
                                    breakeven = True
                                if breakeven:
                                    price_stop *= 1.001
                                price_for_traling_stop *= 1.002
                            if price_stop < float(data['k']['c']) <= price_average and not average:
                                a = buy_order(self.pair, self.dollars_for_order * 1.5, price_buy)
                                price_take = a['entry_price'] * 1.01
                                price_for_traling_stop = a['entry_price'] * 1.003
                                average = True
                                logger.info(f'{datetime.now()}, {self.pair}, {data["k"]["c"]}, _______________AVERAGE_______________ ')
                                try:
                                    bot.send_message(my_id_tg, f"Усреднение по паре - {self.pair}")
                                except Exception:
                                    logger.info(f'Не отправилось сообщение об усреднении по паре {self.pair}')
            except Exception as error:
                logger.info(f'{datetime.now()}, {self.pair}, {error}')
                try:
                    bot.send_message(my_id_tg, f'{datetime.now()}, {self.pair}, {error}')
                except Exception:
                    continue
                await asyncio.sleep(30)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        for pair in top_volatily():
            adp = Strategy(pair, '1m', 50)
            asyncio.ensure_future(adp.main())
        logger.info(f'start {datetime.now()}')
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        logger.info('Finished!')
        loop.close()