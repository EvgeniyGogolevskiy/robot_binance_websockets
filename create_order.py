import time

from binance.client import Client
from config import api, secret
from datetime import datetime

CLIENT = Client(api, secret)


def size_lot(transaction_amount, price_buy):
    lot = transaction_amount / price_buy

    if price_buy <= transaction_amount:
        lot = round(lot)
    elif transaction_amount < price_buy <= transaction_amount * 10:
        lot = round(lot, 1)
    elif transaction_amount * 10 < price_buy <= transaction_amount * 100:
        lot = round(lot, 2)
    elif transaction_amount * 100 < price_buy <= transaction_amount * 1000:
        lot = round(lot, 3)
    else:
        lot = round(lot, 4)
    return lot


def buy_order(pair, depo, price_buy):
    lot = size_lot(depo, price_buy)
    while True:
        try:
            CLIENT.futures_create_order(symbol=pair, side='BUY', type='MARKET', quantity=lot)
            info = CLIENT.futures_position_information(symbol=pair)
            a = {'entry_price': float(info[0]['entryPrice']), 'amt': float(info[0]['positionAmt'])}
            return a
        except Exception as error:
            print(f' {datetime.now}, {pair}, {error}')
            time.sleep(0.1)


def sell_order(pair, lot):
    while True:
        try:
            CLIENT.futures_create_order(symbol=pair, side='SELL', type='MARKET', quantity=lot)
            break
        except Exception as error:
            print(f' {datetime.now}, {pair}, {error}')
            time.sleep(0.1)
