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
        self.past_data = {'BANANAS': {'bid_ask_avg': [], 'mid_price': [
        ], 'position': []}, 'PEARLS': {'position': []}}
        self.T = 100_000
        self.pearlsSpread = 6
        self.sigmasq = 2.5

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        for product in state.order_depths.keys():

            curr_pos = 0
            t = state.timestamp
            if product in state.position.keys():
                curr_pos = state.position[product]
            self.past_data[product]['position'].append(curr_pos)

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
                                if volume + sell_sum + curr_pos < -LIMIT:
                                    raise RuntimeError()
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

                orders.append(Order(product, bid_price, LIMIT - curr_pos))
                orders.append(Order(product, ask_price, -curr_pos - LIMIT))

                result[product] = orders
        # self.__filter(state, result)
        # self.__print_result(result)
        # self.__print_own_trades(state.own_trades)
        logger.flush(state, result)
        return result
