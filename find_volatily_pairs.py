from binance.client import Client
import pandas as pd
import time

CLIENT = Client()


def analise_volume():
    all_pairs = pd.DataFrame(CLIENT.futures_exchange_info()['symbols'])[['pair', 'quoteAsset']]
    pairs = all_pairs.pair.dropna().unique()
    pairs = pairs[5:]

    print("Count all pair market:", len(pairs))
    list_pair_volume = []

    LIST_IGNORE_PAIR = ['BTCUSDT',
                        'ETHUSDT',
                        'BNBUSDT',
                        'BTCBUSD',
                        'ETHBUSD',
                        'BNBBUSD',
                        'SOLBUSD']

    for cripto_pair in pairs:
        if cripto_pair in LIST_IGNORE_PAIR:
            continue
        time.sleep(0.2)

        try:
            data = pd.DataFrame(CLIENT.futures_klines(symbol=cripto_pair, interval='1m', limit=500))
            volume_pair = data[7].astype(float).sum()
            list_pair_volume.append((cripto_pair, volume_pair))
        except Exception as error:
            print(error)
            continue
    if len(list_pair_volume) != 0:
        sorted_list_pair_volume = sorted(list_pair_volume, key=lambda volume: volume[1], reverse=True)
        fix_pecent_list_pair = sorted_list_pair_volume[:int((len(list_pair_volume) * 11) / 100)]
        fix_pecent_list_pair = [pair[0] for pair in fix_pecent_list_pair]
        print(fix_pecent_list_pair)
        return fix_pecent_list_pair
    else:
        return None


def top_volatily():
    list_top_pairs_volatily = []
    all_pairs = pd.DataFrame(CLIENT.futures_exchange_info()['symbols'])[['pair', 'quoteAsset']]
    pairs = all_pairs.pair.dropna().unique()

    for pair in pairs:
        try:
            data = CLIENT.futures_klines(symbol=pair, interval='1m', limit=300)
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
    print(top)
    return top
