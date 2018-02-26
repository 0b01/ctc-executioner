from dateutil import parser
from order_side import OrderSide
import numpy as np
import random
from sklearn.preprocessing import MinMaxScaler


class OrderbookEntry(object):

    def __init__(self, price, qty):
        self.price = price
        self.qty = qty

    def __str__(self):
        return str(self.price) + ": " + str(self.qty)

    def __repr__(self):
        return str(self)

    def getPrice(self):
        return self.price

    def getQty(self):
        return self.qty


class OrderbookState(object):

    def __init__(self, tradePrice=0.0, timestamp=None):
        self.tradePrice = tradePrice
        self.volume = 0.0
        self.timestamp = timestamp
        self.buyers = []
        self.sellers = []
        self.market = {}

    def __str__(self):
        s = '----------ORDERBOOK STATE----------\n'
        s = s + "DateTime: " + str(self.timestamp) + "\n"
        s = s + "Price: " + str(self.tradePrice) + "\n"
        s = s + "Buyers: " + str(self.buyers) + "\n"
        s = s + "Sellers: " + str(self.sellers) + "\n"
        s = s + "Market Vars: " + str(self.market) + "\n"
        s = s + '----------ORDERBOOK STATE----------\n'
        return s

    def __repr__(self):
        return str(self)

    def setTradePrice(self, tradePrice):
        self.tradePrice = tradePrice

    def getTradePrice(self):
        return self.tradePrice

    def setVolume(self, volume):
        self.volume = volume

    def getVolume(self):
        return self.volume

    def getMarket(self):
        return self.market

    def getMarketVar(self, key):
        return self.market[key]

    def setMarketVar(self, key, value):
        self.market[key] = value

    def addBuyer(self, entry):
        self.buyers.append(entry)

    def addBuyers(self, entries):
        for entry in entries:
            self.buyers.append(entry)

    def addSeller(self, entry):
        self.sellers.append(entry)

    def addSellers(self, entries):
        for entry in entries:
            self.sellers.append(entry)

    def getBuyers(self):
        return self.buyers

    def getSellers(self):
        return self.sellers

    def getTimestamp(self):
        return self.timestamp

    def getBidAskMid(self):
        firstBuy = self.getBuyers()[0]
        firstSell = self.getSellers()[0]
        return (firstBuy.getPrice() + firstSell.getPrice()) / 2.0

    def getBestAsk(self):
        return self.getSellers()[0].getPrice()

    def getBestBid(self):
        return self.getBuyers()[0].getPrice()

    def getSidePositions(self, side):
        if side == OrderSide.BUY:
            return self.getBuyers()
        elif side == OrderSide.SELL:
            return self.getSellers()

    def getBasePrice(self, side):
        return self.getSidePositions(side)[0].getPrice()

    def getPriceAtLevel(self, side, level):
        """ Returns price at a certain level of the orderbook.
        In case not enough levels are present in the orderbook, we assume
        linear price increase (seller side) / decrease (buyer side) for the
        following levels.
        """
        positions = self.getSidePositions(side)
        delta = 0.0001 * self.getBestAsk()  # 1 basis point
        if side == OrderSide.BUY:
            # print("level: " + str(level) + ", price: " + str(self.getBestAsk()) + " -> " + str(level * delta) + " -> " + str(self.getBestAsk() + level * delta))
            return self.getBestAsk() + level * delta
        else:
            # print("level: " + str(level) + ", price: " + str(self.getBestAsk()) + " -> " + str(level * delta) + " -> " + str(self.getBestAsk() - level * delta))
            return self.getBestAsk() - level * delta

        # level = abs(level)
        # if level < len(positions):
        #     return positions[level].getPrice()
        #
        # # Estimate subsequent levels
        # derivative_price = np.mean(np.gradient([x.getPrice() for x in positions]))
        # missingLevels = level - len(positions)
        # priceEnd = positions[-1].getPrice()
        # priceEstimated = priceEnd + missingLevels * derivative_price
        # return priceEstimated

class Orderbook(object):

    def __init__(self, extraFeatures=True):
        self.states = []
        self.extraFeatures = extraFeatures

    def __str__(self):
        s = ''
        i = 1
        for state in self.states:
            s = s + 'State ' + str(i) + "\n"
            s = s + '-------' + "\n"
            s = s + str(state)
            s = s + "\n\n"
            i = i + 1
        return s

    def __repr__(self):
        return str(self)

    def addState(self, state):
        self.states.append(state)

    def addStates(self, states):
        for state in states:
            self.states.append(state)

    def getStates(self):
        return self.states

    def getState(self, index):
        if len(self.states) <= index:
            raise Exception('Index out of orderbook state.')
        return self.states[index]

    def getOffsetHead(self, offset):
        """The index (from the beginning of the list) of the first state past
        the given offset in seconds.
        For example, if offset=3 with 10 states availble, whereas for
        simplicity every state has 1 second diff, then the resulting index
        would be the one marked with 'i':

        |x|x|x|i|_|_|_|_|_|_|

        As a result, the elements marked with 'x' are not meant to be used.
        """
        if offset == 0:
            return 0

        states = self.getStates()
        startState = states[0]
        offsetIndex = 0
        consumed = 0.0
        while(consumed < offset and offsetIndex < len(states)-1):
            offsetIndex = offsetIndex + 1
            state = states[offsetIndex]
            consumed = (state.getTimestamp() - startState.getTimestamp()).total_seconds()

        if consumed < offset:
            raise Exception('Not enough data for offset. Found states for '
                            + str(consumed) + ' seconds, required: '
                            + str(offset))

        return offsetIndex

    def getOffsetTail(self, offset):
        """The index (from the end of the list) of the first state past
        the given offset in seconds.
        For example, if offset=3 with 10 states availble, whereas for
        simplicity every state has 1 second diff, then the resulting index
        would be the one marked with 'i':

        |_|_|_|_|_|_|i|x|x|x|

        As a result, the elements marked with 'x' are not meant to be used.
        """
        states = self.getStates()
        if offset == 0:
            return len(states) - 1

        offsetIndex = len(states) - 1
        startState = states[offsetIndex]
        consumed = 0.0
        while(consumed < offset and offsetIndex > 0):
            offsetIndex = offsetIndex - 1
            state = states[offsetIndex]
            consumed = (startState.getTimestamp() - state.getTimestamp()).total_seconds()

        if consumed < offset:
            raise Exception('Not enough data for offset. Found states for '
                            + str(consumed) + ' seconds, required: '
                            + str(offset))

        return offsetIndex

    def getIndexWithTimeRemain(self, seconds, offset=0):
        """ Returns the state with seconds remaining starting from the end.
        For example, if seconds=3 and offset=1 with 10 states availble, whereas
        for simplicity every state has 1 second diff, then the resulting index
        would be the one marked with 'i' and 'x' indicating the non-usable
        elements capped by the offset. This function uses tail based
        offsetting:

        |_|_|_|_|_|_|i>|>|>|x|

        As a result, the maximum seconds to retrieve would be 8, however only 3
        (starting at the index position i>) are used in this case and 6 are not
        being used (marked with '_').
        """
        if not self.getStates():
            raise Exception('Order book does not contain states.')

        states = self.getStates()
        index = self.getOffsetTail(offset)
        endState = states[index]
        consumed = 0.0
        while(consumed < seconds and index > 0):
            index = index - 1
            state = states[index]
            consumed = (endState.getTimestamp() - state.getTimestamp()).total_seconds()

        if consumed < seconds:
            raise Exception('Not enough data available. Found states for '
                            + str(consumed) + ' seconds, required: '
                            + str(seconds))
        return index

    def getTotalDuration(self, offset=0):
        """Time span of data in seconds.
        The offset fixes the pointer starting from the beginning of the data
        feed.

        This function uses per default tail based offsetting.
        """
        states = self.getStates()
        offsetIndex = self.getOffsetTail(offset)
        start = states[0].getTimestamp()
        end = states[offsetIndex].getTimestamp()
        return (end - start).total_seconds()

    def getRandomOffset(self, offset_max=120):
        """Random offset for tail based indexing.
        From the beginning of the state list the required seconds will be
        secured, then the leftover of seconds can be used to randomize offsets.

        For example, if offset_max=3 (market with '_') with a total of 10
        states available, whereas for simplicity every state has 1 second diff,
        then offset can be either of the indices market with 'o':

        |_|_|_|o|o|o|o|o|o|o|

        Therefore, it is always ensured that at least 3 seconds worth of states
        will be availble.
        """
        offsetHead = self.getOffsetHead(offset=offset_max)
        states = self.getStates()
        start = states[offsetHead].getTimestamp()
        end = states[-1].getTimestamp()
        remaining = int((end - start).total_seconds())
        if remaining == 0:
            return 0
        else:
            return random.choice(range(remaining))


    def getRandomState(self, runtime, offset_max):
        offsetTail = self.getRandomOffset(offset_max)
        index = self.getIndexWithTimeRemain(runtime, offsetTail)
        if index >= len(self.getStates()):
            raise Exception('Index out of orderbook state.')
        return self.getState(index), index

    def createArtificial(self, config):
        startPrice = config['startPrice']
        endPrice = config['endPrice']
        levels = config['levels']
        qtyPosition = config['qtyPosition']
        startTime = config['startTime']
        duration = config['duration']
        interval = config['interval']
        steps = duration / interval
        gradient = (endPrice - startPrice) / steps
        steps = int(steps + 1)
        prices = [startPrice + i*gradient for i in range(steps)]
        times = [startTime + i*interval for i in range(steps)]
        for i in range(steps):
            p = prices[i]
            t = times[i]
            bps = 0.0001 * p
            asks = [OrderbookEntry(price=(p + i * bps), qty=qtyPosition) for i in range(levels)]
            bids = [OrderbookEntry(price=(p - (i+1) * bps), qty=qtyPosition) for i in range(levels)]
            s = OrderbookState(tradePrice=p, timestamp=t)
            s.addBuyers(bids)
            s.addSellers(asks)
            self.addState(s)


    def loadFromFile(self, file):
        import csv
        with open(file, 'rt') as tsvin:
            tsvin = csv.reader(tsvin, delimiter='\t')
            for row in tsvin:
                p = float(row[1])
                vol = float(row[2])
                b1 = float(row[3])
                b2 = float(row[4])
                b3 = float(row[5])
                b4 = float(row[6])
                b5 = float(row[7])
                a1 = float(row[8])
                a2 = float(row[9])
                a3 = float(row[10])
                a4 = float(row[11])
                a5 = float(row[12])
                bq1 = float(row[13])
                bq2 = float(row[14])
                bq3 = float(row[15])
                bq4 = float(row[16])
                bq5 = float(row[17])
                aq1 = float(row[18])
                aq2 = float(row[19])
                aq3 = float(row[20])
                aq4 = float(row[21])
                aq5 = float(row[22])
                dt = parser.parse(row[24])  # trade timestamp as reference
                buyers = [
                    OrderbookEntry(b1, bq1),
                    OrderbookEntry(b2, bq2),
                    OrderbookEntry(b3, bq3),
                    OrderbookEntry(b4, bq4),
                    OrderbookEntry(b5, bq5)
                ]
                sellers = [
                    OrderbookEntry(a1, aq1),
                    OrderbookEntry(a2, aq2),
                    OrderbookEntry(a3, aq3),
                    OrderbookEntry(a4, aq4),
                    OrderbookEntry(a5, aq5)
                ]
                s = OrderbookState(tradePrice=p, timestamp=dt)
                s.addBuyers(buyers)
                s.addSellers(sellers)
                s.setVolume(vol)
                # Hand made features
                if self.extraFeatures:
                    mean60 = float(row[26])
                    vol60 = float(row[27])
                    std60 = float(row[28])
                    s.setMarketVar('mean60', mean60)
                    s.setMarketVar('vol60', vol60)
                    s.setMarketVar('std60', std60)

                self.addState(s)


    def loadFromBitfinexFile(self, file):
        import csv
        import json
        with open(file, 'rt') as tsvin:
            tsvin = csv.reader(tsvin, delimiter='\t')
            for row in tsvin:
                priceBid = float(row[1])
                priceAsk = float(row[2])
                volumeBid = float(row[3])
                volumeAsk = float(row[4])
                volume = float(row[5])
                bids = json.loads(row[6])
                asks = json.loads(row[7])
                timestamp = parser.parse(row[8])

                buyers = [OrderbookEntry(price=float(x['price']), qty=float(x['amount'])) for x in bids]
                sellers = [OrderbookEntry(price=float(x['price']), qty=float(x['amount'])) for x in asks]

                s = OrderbookState(tradePrice=priceAsk, timestamp=timestamp)
                s.addBuyers(buyers)
                s.addSellers(sellers)
                s.setVolume(volume)
                s.setMarketVar(key='volumeBid', value=volumeBid)
                s.setMarketVar(key='volumeAsk', value=volumeAsk)
                self.addState(s)

    @staticmethod
    def generateDictFromEvents(events_pd):
        import copy
        most_recent_orderbook = {"bids": {}, "asks": {}}
        orderbook = {}
        for seq, e in events_pd.iterrows():
            if e.is_trade:
                continue

            if e["size"] == 0.0:
                try:
                    del most_recent_orderbook["bids" if e.is_bid else "asks"][e.price]
                    # print('Cancel ' + str(e.price))
                except:
                    # print('Cancel ' + str(e.price) + ' not in recent book')
                    continue
            else:
                current_size = most_recent_orderbook["bids" if e.is_bid else "asks"].get(e.price, 0.0)
                most_recent_orderbook["bids" if e.is_bid else "asks"][e.price] = current_size + e["size"]

            orderbook[e.ts] = copy.deepcopy(most_recent_orderbook)
        return orderbook

    def loadFromDict(self, d):
        import collections

        # skip states until at least 1 bid and 1 ask is available
        while True:
            head = d[list(d.keys())[0]]
            if len(head["bids"]) > 0 and len(head["asks"]) > 0:
                break
            del d[list(d.keys())[0]]

        for ts, state in d.items():
            bids = collections.OrderedDict(sorted(state["bids"].items(), reverse=True))
            asks = collections.OrderedDict(sorted(state["asks"].items()))
            buyers = [OrderbookEntry(price=float(x[0]), qty=float(x[1])) for x in bids.items()]
            sellers = [OrderbookEntry(price=float(x[0]), qty=float(x[1])) for x in asks.items()]
            if len(sellers) > 0:
                s = OrderbookState(tradePrice=max(state["asks"].keys()), timestamp=ts)
                s.addBuyers(buyers)
                s.addSellers(sellers)
                s.setVolume(0.0)
                self.addState(s)

        #for s in self.getStates():
        #    assert(s.getBestBid() <= s.getBestAsk())

    def loadFromEvents(self, events_pd):
        d = Orderbook.generateDictFromEvents(events_pd)
        self.loadFromDict(d)

    def plot(self, show_bidask=False, max_level=-1):
        import matplotlib.pyplot as plt
        price = [x.getBidAskMid() for x in self.getStates()]
        times = [x.getTimestamp() for x in self.getStates()]
        plt.plot(times, price)
        if show_bidask:
            buyer = [x.getBuyers()[max_level].getPrice() for x in self.getStates()]
            seller = [x.getSellers()[max_level].getPrice() for x in self.getStates()]
            plt.plot(times, buyer)
            plt.plot(times, seller)
        plt.show()

    def createFeatures(self):
        volumes = np.array([x.getVolume() for x in self.getStates()])
        scaler = MinMaxScaler(feature_range=(0, 5))
        volumesScaled = scaler.fit_transform(volumes.reshape(-1, 1))
        volumesScaled = volumesScaled.flatten().tolist()
        volumesRelative = list(map(round, volumesScaled))
        i = 0
        for state in self.getStates():
            state.setMarketVar('volumeRelativeTotal', volumesRelative[i])
            i = i + 1

# import pandas as pd
# cols = ["ts", "seq", "size", "price", "is_bid", "is_trade"] #, "ttype"]
# events = pd.read_table('../ctc-orderbook/ob-1.tsv', sep='\t', names=cols, index_col="seq")
# o = Orderbook()
# o.loadFromEvents(events)
# o.plot()

#o = Orderbook()
#o.loadFromBitfinexFile('../ctc-executioner/orderbook_bitfinex_btcusd_view.tsv')
#o.loadFromFile('query_result_train_15m.tsv')
#o.plot()
#o.createFeatures()
#print([x.getMarketVar('volumeRelativeTotal') for x in o.getStates()])
#print(o.getState(0))
#print(o.getState(200))

# print(o.getState(0))
# print(o.getState(1))
# print(o.getState(2))

# import datetime
# orderbook = Orderbook()
# config = {
#     'startPrice': 10010.0,
#     'endPrice': 10000.0,
#     'levels': 25,
#     'qtyPosition' : 1.0,
#     'startTime': datetime.datetime.now(),
#     'duration': datetime.timedelta(seconds=100),
#     'interval': datetime.timedelta(seconds=10),
# }
# orderbook.createArtificial(config)
# orderbook.plot()
# print('states: ' + str(len(orderbook.getStates())))
# st, index = orderbook.getRandomState(runtime=60, offset_max=60)
# print(index)
#o = Orderbook()
#o.loadFromFile('query_result_small.tsv')

# print(o.getTotalDuration(offset=0))
# print(o.getOffsetTail(offset=0))
# print(o.getOffsetTail(offset=16))
#
# print(o.getRandomOffset(offset_max=60))
# print(o.getIndexWithTimeRemain(seconds=60, offset=50))
# s0 = o.getState(0).getTimestamp()
# s1 = o.getState(1).getTimestamp()
# print(s0)
# print("")
# print(s1)
# print("")
# print((s1-s0).total_seconds())
