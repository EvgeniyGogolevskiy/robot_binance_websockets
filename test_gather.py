import asyncio
import websockets
import json
import pandas as pd
from binance.client import Client
from datetime import datetime

client = Client()

all_symbols = pd.DataFrame(client.futures_exchange_info()['symbols'])[['pair', 'quoteAsset']]
symbols = all_symbols.pair.dropna().unique()[20:30]
interval = '1m'


async def subscribe_to_klines(symbol):
    async with websockets.connect(f"wss://fstream.binance.com/ws/{symbol.lower()}@kline_{interval}") as ws:
        subscribe_msg = json.dumps({
            "method": "SUBSCRIBE",
            "params": [f"{symbol}@kline_{interval}"],
            "id": 1
        })
        await ws.send(subscribe_msg)
        while True:
            try:
                message = await ws.recv()
                msg = json.loads(message)
                if msg['e'] != 'kline':
                    continue
                if float(msg['k']['c']) > float(msg['k']['o'])*1.002:
                    print(msg['k']['s'])
            except Exception as error:
                print(error)
                continue


async def main():
    tasks = [subscribe_to_klines(symbol) for symbol in symbols]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
