from datetime import datetime
import websockets
import asyncio
import json
from scipy.stats import pearsonr
from binance.client import Client

CLIENT = Client()


class DiffPrice:
    def __init__(self, pair):
        self.pair: str = pair
        self.list_eth: list[float] = []
        self.list_btc: list[float] = []

    async def main(self):
        url = f'wss://fstream.binance.com/stream?streams={self.pair.lower()}@markPrice@1s/btcusdt@markPrice@1s'
        print(datetime.now(), ' start')
        async with websockets.connect(url) as client:
            while True:
                data = json.loads(await client.recv())
                if len(self.list_eth) < 3600:
                    if data['data']['s'] == 'BTCUSDT':
                        self.list_btc.append(float(data['data']['p']))
                    if data['data']['s'] == 'ETHUSDT':
                        self.list_eth.append(float(data['data']['p']))
                else:
                    if data['data']['s'] == 'BTCUSDT':
                        self.list_btc = self.list_btc[1:] + [float(data['data']['p'])]
                    if data['data']['s'] == 'ETHUSDT':
                        self.list_eth = self.list_eth[1:] + [float(data['data']['p'])]
                    coef = pearsonr(self.list_btc, self.list_eth)[0]
                    diff_eth = (self.list_eth[0] - self.list_eth[-1]) * 100 / self.list_eth[0]
                    diff_only_eth = diff_eth * (1 - coef)
                    print(f'{datetime.now()}, коэф = {coef}, движ по рынку = {diff_eth}, собств движ = {diff_only_eth}, старое значение = {self.list_eth[0]}, новое значение = {self.list_eth[-1]}')
                    if abs(diff_only_eth) >= 1:
                        print('Собственное движение цены на фьючерс ETHUSDT больше 1%')


if __name__ == "__main__":
    dp = DiffPrice('ETHUSDT')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dp.main())

# херня полная
# попробовать стягивать цену со свечей двумя разными функциями
# 
#