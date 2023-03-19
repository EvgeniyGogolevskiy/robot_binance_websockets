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
