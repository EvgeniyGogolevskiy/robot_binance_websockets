import statistics


def calculate_volume_diff_first(data_5m):
    data_5m_volume_buy = list(data_5m[10][18:29])
    data_5m_volume = list(data_5m[7][18:29])
    list_volume_diff = []
    list_volume = []
    for i in range(len(data_5m_volume)):
        volume_sell = float(data_5m_volume[i]) - float(data_5m_volume_buy[i])
        try:
            volume_diff = float(data_5m_volume_buy[i]) / volume_sell
        except ZeroDivisionError:
            volume_diff = 1
        list_volume_diff.append(volume_diff)
        list_volume.append(float(data_5m_volume[i]))
    average_vol = round(statistics.mean(list_volume[:-1]), 2)
    v = {'list_volume': list_volume, 'list_volume_diff': list_volume_diff, 'average_vol': average_vol}
    return v


def calculate_diff_volume(data, list_volume, list_volume_diff):
    volume_sell = float(data['k']['q']) - float(data['k']['Q'])
    list_volume = list_volume[1:] + [float(data['k']['q'])]
    try:
        volume_diff = float(data['k']['Q']) / volume_sell
    except ZeroDivisionError:
        volume_diff = 1
    list_volume_diff = list_volume_diff[1:] + [volume_diff]
    average_vol = round(statistics.mean(list_volume[:-1]), 2)
    v = {'list_volume': list_volume, 'list_volume_diff': list_volume_diff, 'average_vol': average_vol}
    return v


def calculate_diff_first(data_5m):
    data_5m_high = list(data_5m[2][18:29])
    data_5m_low = list(data_5m[3][18:29])
    data_high_ma = list(map(float, data_5m[2][28:30]))
    list_diff = []
    for i in range(len(data_5m_high)):
        list_diff.append((float(data_5m_high[i]) - float(data_5m_low[i])) * 100 / float(data_5m_high[i]))
    average_diff = round(statistics.mean(list_diff[:-1]), 2)
    average_diff5 = round(statistics.mean(list_diff[-6:-1]), 2)
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'data_high_ma': data_high_ma, 'average_diff5': average_diff5}
    return a


def calculate_diff(data, list_diff, data_high_ma):
    diff = (float(data['k']['h']) - float(data['k']['l'])) * 100 / float(data['k']['h'])
    data_high_ma = data_high_ma[1:] + [float(data['k']['h'])]
    list_diff = list_diff[1:] + [diff]
    average_diff = round(statistics.mean(list_diff[:-1]), 2)
    average_diff5 = round(statistics.mean(list_diff[-6:-1]), 2)
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'data_high_ma': data_high_ma, 'average_diff5': average_diff5}
    return a
