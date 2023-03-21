import statistics


def calculate_volume_first(data_5m):
    data_5m_volume_buy = list(data_5m[10][19:29])
    data_5m_volume = list(data_5m[7][19:29])
    list_volume_diff = []
    for i in range(len(data_5m_volume)):
        volume_sell = float(data_5m_volume[i]) - float(data_5m_volume_buy[i])
        volume_diff = float(data_5m_volume_buy[i]) - volume_sell
        list_volume_diff.append(volume_diff)
    return list_volume_diff


def calculate_volume(data, list_volume_diff):
    volume_sell = float(data['k']['q']) - float(data['k']['Q'])
    volume_diff = float(data['k']['Q']) - volume_sell
    list_volume_diff = list_volume_diff[1:] + [volume_diff]
    return list_volume_diff


def calculate_diff_first(data_5m):
    data_5m_hight = list(data_5m[2][19:29])
    data_5m_low = list(data_5m[3][19:29])
    list_diff = []
    for i in range(len(data_5m_hight)):
        list_diff.append((float(data_5m_hight[i]) - float(data_5m_low[i])) * 100 / float(data_5m_hight[i]))
    average_diff = statistics.mean(list_diff)
    min10 = min(list(map(float, data_5m_low)))
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'min10': min10, 'data_5m_low': data_5m_low}
    return a


def calculate_diff(data, list_diff, data_5m_low):
    diff = (float(data['k']['h']) - float(data['k']['l'])) * 100 / float(data['k']['h'])
    data_5m_low = data_5m_low[1:] + [data['k']['l']]
    list_diff = list_diff[1:] + [diff]
    average_diff = statistics.mean(list_diff)
    min10 = min(list(map(float, data_5m_low)))
    a = {'list_diff': list_diff, 'average_diff': average_diff, 'min10': min10, 'data_5m_low': data_5m_low}
    return a
