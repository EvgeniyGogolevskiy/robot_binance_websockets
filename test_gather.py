import asyncio
import websockets
import json


async def get_candle_data(symbols):
    websockets_dict = {}
    for symbol in symbols:
        websocket = await websockets.connect(f"wss://fstream.binance.com/ws/{symbol.lower()}@kline_1m")
        websockets_dict[symbol] = websocket
    while True:
        try:
            for symbol, websocket in websockets_dict.items():
                candle_data = await asyncio.wait_for(websocket.recv(), timeout=10)
                candle_data = json.loads(candle_data)
                # обработка свечных данных
                print(f"{symbol} candle data: {candle_data}")
        except asyncio.exceptions.TimeoutError:
            for symbol, websocket in websockets_dict.items():
                await websocket.close()
            break
        except Exception as e:
            print(f"Error while getting candle data: {e}")
            for symbol, websocket in websockets_dict.items():
                await websocket.close()
            break


async def main():
    symbols = ["CTSIUSDT", "CFXUSDT", "ARB"]
    await get_candle_data(symbols)


asyncio.run(main())

#   ["CTSIUSDT", "CFXUSDT", "ARB"]
