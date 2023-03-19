from binance.client import Client
import pandas as pd
import time

CLIENT = Client()


def top_volatily():
    list_top_pairs_volatily = []
    all_pairs = pd.DataFrame(CLIENT.futures_exchange_info()['symbols'])[['pair', 'quoteAsset']]
    pairs = all_pairs.pair.dropna().unique()

    for pair in pairs:
        try:
            data = CLIENT.futures_klines(symbol=pair, interval='30m', limit=8)
        except Exception as error:
            print(f"По паре {pair} не удалось скачать данные по свечам", error)
            continue

        df = pd.DataFrame(data)
        df = df.rename(columns={1: 'Open', 2: 'High', 3: 'Low', 4: 'Close'})[['Open', 'High', 'Low', 'Close']].astype(
            float)
        df['volatily'] = df.apply(lambda x: abs((((x['Low'] * 100) / (x['High'])) - 100)), axis=1)
        volatily = round(df.volatily.median(), 2)
        list_top_pairs_volatily.append((pair, volatily))
        time.sleep(0.1)

    list_top_pairs_volatily = sorted(list_top_pairs_volatily, key=lambda volume: volume[1], reverse=True)
    list_top_pairs_volatily = list_top_pairs_volatily[:25]
    top = []
    for i in range(len(list_top_pairs_volatily)):
        top.append(list_top_pairs_volatily[i][0])
    return top