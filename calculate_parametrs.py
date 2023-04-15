import statistics


def calculate_volume_diff_first(data_5m):
    data_5m_volume_buy = list(data_5m[10][19:29])
    data_5m_volume = list(data_5m[7][19:29])
    list_volume_diff = []
    for i in range(len(data_5m_volume)):
        volume_sell = float(data_5m_volume[i]) - float(data_5m_volume_buy[i])
        volume_diff = float(data_5m_volume_buy[i]) / volume_sell
        list_volume_diff.append(volume_diff)
    return list_volume_diff


def calculate_diff_volume(data, list_volume_diff):
    volume_sell = float(data['k']['q']) - float(data['k']['Q'])
    try:
        volume_diff = float(data['k']['Q']) / volume_sell
    except ZeroDivisionError:
        volume_diff = 1
    list_volume_diff = list_volume_diff[1:] + [volume_diff]
    return list_volume_diff


def calculate_diff_first(data_5m):
    data_5m_high = list(data_5m[2][25:30])
    data_5m_low = list(data_5m[3][25:30])
    data_close = list(map(float, data_5m[4][26:30]))
    data_close9 = list(map(float, data_5m[4][21:30]))
    list_diff = []
    for i in range(len(data_5m_high)):
        list_diff.append((float(data_5m_high[i]) - float(data_5m_low[i])) * 100 / float(data_5m_high[i]))
    average_diff = round(statistics.mean(list_diff),2)
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'data_close': data_close, 'data_close9': data_close9}
    return a


def calculate_diff(data, list_diff, data_5m_close):
    diff = (float(data['k']['h']) - float(data['k']['l'])) * 100 / float(data['k']['h'])
    data_close = data_5m_close[1:] + [float(data['k']['c'])]
    data_close9 = data_5m_close[1:] + [float(data['k']['c'])]
    list_diff = list_diff[1:] + [diff]
    average_diff = round(statistics.mean(list_diff),2)
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'data_close': data_close, 'data_close9': data_close9}
    return a
