from typing import Dict, List
from datamodel import Order, ProsperityEncoder, TradingState, Symbol, OrderDepth
import math
import json
import numpy as np
import statistics as st

# https://bz97lt8b1e.execute-api.eu-west-1.amazonaws.com/prod/results/tutorial/<algorithm id>


class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: Dict[Symbol, List[Order]]) -> None:
        logs = self.logs
        if logs.endswith("\n"):
            logs = logs[:-1]

        print(json.dumps({
            "state": state,
            "orders": orders,
            "logs": logs,
        }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True))

        self.state = None
        self.orders = {}
        self.logs = ""


logger = Logger()


class Trader:
    def __init__(self):
        self.data = {'BANANAS': {'buy_price': [], 'sell_price': [], 'avg_buy_price': 0, 'avg_sell_price': 0},
                     'PEARLS': {'buy_price': [], 'sell_price': [], 'avg_buy_price': 0, 'avg_sell_price': 0},
                     'COCONUTS': {'buy_price': [], 'sell_price': [], 'avg_buy_price': 0, 'avg_sell_price': 0, 'mid_price': []},
                     'PINA_COLADAS': {'buy_price': [], 'sell_price': [], 'avg_buy_price': 0, 'avg_sell_price': 0, 'mid_price': []}}
        self.T = 1_000_000
        self.pearlsSpread = 6
        self.sigmasq = 2.5
        self.coconut_sigmasq = 1

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        for product in state.order_depths.keys():

            curr_pos = 0
            t = state.timestamp
            if product in state.position.keys():
                curr_pos = state.position[product]

            if product in state.own_trades.keys():
                for trade in state.own_trades[product]:
                    if trade.buyer == 'SUBMISSION':
                        if curr_pos >= 0:
                            self.data[product]['avg_buy_price'] = (
                                self.data[product]['avg_buy_price']*curr_pos + trade.price*trade.quantity)/(curr_pos+trade.quantity)
                    elif trade.seller == "SUBMISSION":
                        if curr_pos <= 0:
                            self.data[product]['avg_sell_price'] = (
                                self.data[product]['avg_sell_price']*(-curr_pos) + trade.price*trade.quantity)/((-curr_pos)+trade.quantity)

            if product == 'PEARLS':
                LIMIT = 20
                order_depth: OrderDepth = state.order_depths[product]
                orders: list[Order] = []
                acceptable_price = 10_000
                buy_sum = 0
                sell_sum = 0

                if len(order_depth.sell_orders) > 0:
                    asks = list(order_depth.sell_orders.keys())
                    asks.sort()
                    for ask in asks:
                        if ask <= acceptable_price:
                            volume = abs(order_depth.sell_orders[ask])
                            if buy_sum + curr_pos + volume > LIMIT:
                                volume = LIMIT - curr_pos - buy_sum
                            if volume > 0:
                                buy_sum = buy_sum + volume
                                orders.append(Order(product, ask, volume))

                if len(order_depth.buy_orders) > 0:
                    bids = list(order_depth.buy_orders.keys())
                    bids.sort(reverse=True)
                    for bid in bids:
                        if bid >= acceptable_price:
                            volume = -abs(order_depth.buy_orders[bid])
                            if volume + curr_pos + sell_sum < -LIMIT:
                                volume = -LIMIT - curr_pos - sell_sum
                            if volume < 0:
                                sell_sum = sell_sum + volume
                                orders.append(Order(product, bid, volume))
                spread = 6

                if buy_sum + curr_pos < LIMIT:
                    orders.append(
                        Order(product, acceptable_price-spread/2, LIMIT-curr_pos-buy_sum))
                if sell_sum + curr_pos > -LIMIT:
                    orders.append(
                        Order(product, acceptable_price+spread/2, -sell_sum-LIMIT-curr_pos))

                result[product] = orders

            if product == 'BANANAS':

                LIMIT = 20
                buy_sum = 0
                sell_sum = 0

                order_depth: OrderDepth = state.order_depths[product]
                orders: list[Order] = []

                avg_s = sum([order_depth.sell_orders[key] *
                            key for key in order_depth.sell_orders.keys()])/sum(order_depth.sell_orders.values())
                avg_b = sum([order_depth.buy_orders[key] *
                            key for key in order_depth.buy_orders.keys()])/sum(order_depth.buy_orders.values())

                r = (avg_s+avg_b)/2 - (curr_pos/20) * \
                    self.sigmasq*(self.T-t)/self.T
                delta = self.sigmasq*(self.T-t)/self.T + 2*np.log(4)

                # INVENTORY CONTROL => current best
                # p_t = (avg_s+avg_b)/2
                # self.past_data[product]['bid_ask_avg'].append(p_t)
                # p_t = p_t - curr_pos * (k1/40)
                # bid_price = p_t - k1/2
                # ask_price = p_t + k1/2
                # orders.append(Order(product, bid_price, LIMIT - curr_pos))
                # orders.append(Order(product, ask_price, -curr_pos - LIMIT))

                bid_price = r-delta/2
                ask_price = r+delta/2

                orders.append(
                    Order(product, bid_price, LIMIT-curr_pos-buy_sum))
                orders.append(
                    Order(product, ask_price, -sell_sum-LIMIT-curr_pos))

                result[product] = orders

            if product == 'COCONUTS':
                vol_time = 100
                std_cap = 3.8
                LIMIT = 600

                buy_sum = 0
                sell_sum = 0

                order_depth: OrderDepth = state.order_depths[product]
                orders: list[Order] = []

                # avg_s = sum([order_depth.sell_orders[key] *
                #             key for key in order_depth.sell_orders.keys()])/sum(order_depth.sell_orders.values())
                # avg_b = sum([order_depth.buy_orders[key] *
                #             key for key in order_depth.buy_orders.keys()])/sum(order_depth.buy_orders.values())
                # avg_order = (avg_b + avg_s)/2

                best_s = min(order_depth.sell_orders.keys())
                best_b = max(order_depth.buy_orders.keys())
                mid_price = (best_s + best_b)/2

                self.data[product]['mid_price'].append(mid_price)

                biased_mid_price = mid_price - 0.48410
                delta = 1.9

                # if len(self.data[product]['mid_price']) > fit:
                #     # m, b = np.polyfit(
                #     #     range(0, fit), self.data[product]['mid_price'][-fit:], 1)
                #     # predicted = m*fit + b
                #     mean = np.mean(self.data[product]['mid_price'][-fit:])

                #     if len(order_depth.sell_orders) > 0:
                #         asks = list(order_depth.sell_orders.keys())
                #         asks.sort()
                #         for ask in asks:
                #             if ask < mean:
                #                 volume = abs(order_depth.sell_orders[ask])
                #                 if buy_sum + curr_pos + volume > LIMIT:
                #                     volume = LIMIT - curr_pos - buy_sum
                #                 if volume > 0:
                #                     buy_sum = buy_sum + volume
                #                     orders.append(Order(product, ask, volume))

                #     if len(order_depth.buy_orders) > 0:
                #         bids = list(order_depth.buy_orders.keys())
                #         bids.sort(reverse=True)
                #         for bid in bids:
                #             if bid > mean:
                #                 volume = -abs(order_depth.buy_orders[bid])
                #                 if volume + curr_pos + sell_sum < -LIMIT:
                #                     volume = -LIMIT - curr_pos - sell_sum
                #                 if volume < 0:
                #                     sell_sum = sell_sum + volume
                #                     orders.append(Order(product, bid, volume))

                r = biased_mid_price - (curr_pos/LIMIT)*3

                bid_price = r-delta/2
                ask_price = r+delta/2

                # self.__clear_position(
                #     product, curr_pos, orders, order_depth.buy_orders, order_depth.sell_orders, delta)
                if len(self.data[product]['mid_price']) > vol_time:
                    std = np.std(self.data[product]['mid_price'][:-vol_time])
                else:
                    std = np.std(self.data[product]['mid_price'])

                if std > std_cap:
                    orders.append(Order(product, mid_price, -curr_pos))
                else:
                    orders.append(
                        Order(product, bid_price, LIMIT-curr_pos-buy_sum))
                    orders.append(
                        Order(product, ask_price, -sell_sum-LIMIT-curr_pos))
                result[product] = orders

            if product == 'PINA_COLADAS':
                vol_time = 100
                std_cap = 9.5
                LIMIT = 300

                order_depth: OrderDepth = state.order_depths[product]
                orders: list[Order] = []

                avg_s = sum([order_depth.sell_orders[key] *
                            key for key in order_depth.sell_orders.keys()])/sum(order_depth.sell_orders.values())
                avg_b = sum([order_depth.buy_orders[key] *
                            key for key in order_depth.buy_orders.keys()])/sum(order_depth.buy_orders.values())
                avg_order = (avg_b + avg_s)/2

                best_s = min(order_depth.sell_orders.keys())
                best_b = max(order_depth.buy_orders.keys())
                mid_price = (best_s + best_b)/2

                biased_mid_price = mid_price - 0.516026
                delta = 1
                r = biased_mid_price - (curr_pos/LIMIT)*3

                bid_price = r-delta/2
                ask_price = r+delta/2

                # self.__clear_position(
                #     product, curr_pos, orders, order_depth.buy_orders, order_depth.sell_orders, delta)

                if len(self.data[product]['mid_price']) > vol_time:
                    std = np.std(self.data[product]['mid_price'][:-vol_time])
                else:
                    std = np.std(self.data[product]['mid_price'])

                if std > std_cap:
                    orders.append(Order(product, mid_price, -curr_pos))
                else:
                    orders.append(
                        Order(product, bid_price, LIMIT-curr_pos-buy_sum))
                    orders.append(
                        Order(product, ask_price, -sell_sum-LIMIT-curr_pos))

                result[product] = orders

        logger.flush(state, result)
        return result

    def __clear_position(self, product_name, curr_position, orders, buy_orders, sell_orders, delta):
        if curr_position > 0:
            if len(buy_orders) > 0:
                prices = list(buy_orders.keys())
                prices.sort(reverse=True)
                sum = 0
                for price in prices:
                    if price > self.data[product_name]['avg_buy_price']+delta/2:
                        if sum < curr_position:
                            orders.append(
                                Order(product_name, price, -abs(buy_orders[price])))
                            sum += abs(buy_orders[price])

        if curr_position < 0:
            if len(sell_orders) > 0:
                prices = list(sell_orders.keys())
                prices.sort()
                sum = 0
                for price in prices:
                    if price < self.data[product_name]['avg_sell_price']-delta/2:
                        if sum < abs(curr_position):
                            orders.append(Order(product_name, price,
                                                abs(sell_orders[price])))
                            sum += abs(sell_orders[price])

    # def __regime_filter(self, product_name, )

    # self.__filter(state, result)
    # self.__print_result(result)
    # self.__print_own_trades(state.own_trades)
