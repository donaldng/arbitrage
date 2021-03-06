from pymongo import MongoClient
import time, json, os, sys, requests, subprocess, config

db = MongoClient().wtracker.trades
db.drop()
order = MongoClient().wtracker.orders
order.drop()

def find_process(ps_name):
    p1=subprocess.Popen(['ps','-ef'],stdout=subprocess.PIPE)
    p2=subprocess.Popen(['grep','python3'],stdin=p1.stdout,stdout=subprocess.PIPE)
    p3=subprocess.Popen(['grep','-i',ps_name],stdin=p2.stdout,stdout=subprocess.PIPE)
    p4=subprocess.Popen(['wc','-l'],stdin=p3.stdout,stdout=subprocess.PIPE)
    output = p4.communicate()[0].decode('utf-8').strip()

    return int(output)


def process_query():
    global eth
    global btc
    global tracker_status
    global oldtime

    os.system("clear")
    print("\n[ Arbitrage ]\n")

    usd = 1000
    result = {}
    price_dict = {}

    latest = db.aggregate([
                            { "$match": { 'pair':{ "$in": form_pair() } } },
                            { "$group": {"_id": "$pair", "doc": { "$last": "$$ROOT" } }},
                            { "$sort": { "ts": -1, "base": -1 } }
                            ])

    for x in latest:
        x = x["doc"]

        price = float(x["price"])
        pair = x["pair"]

        try:
            if pair == "BTCUSD":
                btc = price
            elif pair == "ETHUSD":
                eth = price
            elif btc != 0 and eth != 0:
                if pair[-3:] == "USD":
                    asset = usd / price
                    result.update({pair: asset})
                    price_dict.update({pair: price})
                elif pair[-3:] == "BTC":
                    asset = usd / (btc * price)
                    result.update({pair: asset})
                    price_dict.update({pair: price})
                elif pair[-3:] == "ETH":
                    asset = usd / (eth * price)
                    result.update({pair: asset})
                    price_dict.update({pair: price})

                asset = round(asset, 4)
                price = round(price, 6)
                print("[ %s ] %s -> %s" % (pair, price, asset))
        except:
            pass

    process_result(result,price_dict)


    # Tracker status
    try:
        oldtime = oldtime
    except:
        oldtime = time.time()
        tracker_status = ("ON" if find_process("tracker.py") else "OFF")
    
    if time.time() - oldtime > 20:
        tracker_status = ("ON" if find_process("tracker.py") else "OFF")
        oldtime = time.time()

    print("\nTracker status: %s" % tracker_status)

    if tracker_status == "OFF":
        print("\n*** Tracker is not running, please run command as below:")
        print("python3 tracker.py %s" % symbol)

def process_result(res,price_dict):
    try:
        mx=max(res, key=res.get)
        mn=min(res, key=res.get)
        gap_limit = config.gap_limit # %
        gap = round((((res[mx] / res[mn])-1)-config.fees)*100, 4)

        print("\ngap from %s to %s is %s%%." % (mn, mx, gap))

        if gap > gap_limit:
            print("\nSearch for order:")
            print('long %s @ %s' % (mn, price_dict[mn]))
            print('short %s @ %s' % (mx, price_dict[mx]))

            ts = time.time()

            data = {'ts':ts, 'price': price_dict[mx], 'pair': mx, 'type': 'asks', 'base_cur': get_base_cur(mx)}
            res = order.insert_one(data)
            data = {'ts':ts, 'price': price_dict[mn], 'pair': mn, 'type': 'bids', 'base_cur': get_base_cur(mn)}
            res = order.insert_one(data)
    except:
        pass

def get_base_cur(pair):

    val = 1

    if 'btc' in pair.lower():
        val = btc
    elif 'eth' in pair.lower():
        val = eth

    return val

def form_pair():
    base = ['USD', 'BTC', 'ETH']

    new_pair = ['BTCUSD','ETHUSD']

    for b in base:
        p = "%s%s" % (symbol, b)

        new_pair.append(p)

    return new_pair


def main():
    global global_price
    global symbol
    global currency

    symbol = str(sys.argv[1]).upper()

    pid=os.fork()
    if pid==0:
        ppid = os.getpid()
        os.system("nohup python3 tracker/tracker.py %s %s >/dev/null 2>&1 &" % (symbol, ppid))
        os._exit(0)    

    while(1):
        process_query()
        time.sleep(1)



if __name__== "__main__":
    if len(sys.argv) > 1:
        main()

    print("Error: param 1 coin input needed! E.g. IOT / BCH / BCC")

