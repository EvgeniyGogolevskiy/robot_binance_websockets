import asyncio
import datetime
import pandas as pd

from binance import AsyncClient, BinanceSocketManager, Client


async def main():
    cl = Client()
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    ts = bm.aggtrade_futures_socket('XRPUSDT')
    # then start receiving messages
    async with ts as tscm:
        info_per_hour = pd.DataFrame(cl.futures_klines(symbol='XRPUSDT', interval='1m', limit=60))
        max_price_per_hour = float(info_per_hour.max()[2])
        print(f'Максимальная цена за последний час {max_price_per_hour}')
        while True:
            time_now = datetime.datetime.now()
            last_symbol_second = str(time_now.second)[-1]
            if last_symbol_second == '0' or last_symbol_second == '5':
                info_per_hour = pd.DataFrame(cl.futures_klines(symbol='XRPUSDT', interval='1m', limit=60))
                max_price_per_hour = float(info_per_hour.max()[2])
                print(f'Максимальная цена за последний час {max_price_per_hour}')
            res = await tscm.recv()
            price_now = float(res['data']['p'])
            if price_now > max_price_per_hour:
                max_price_per_hour = price_now
                print(f'Теперь максимальная цена {max_price_per_hour}')
            if price_now <= max_price_per_hour * 0.99:
                print(f'Цена ({price_now}) стала ниже на 1% чем максимальная за последний час ({max_price_per_hour})')

    await client.close_connection()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
