from typing import Dict, List
from datamodel import Order, ProsperityEncoder, TradingState, Symbol, OrderDepth
import math
import json
import numpy as np

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

pastData = {}


class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        for product in state.order_depths.keys():

            curr_pos = 0
            if product in state.position.keys():
                curr_pos = state.position[product]

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
                        if ask < acceptable_price:
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
                        if bid > acceptable_price:
                            volume = -abs(order_depth.buy_orders[bid])
                            if volume + curr_pos + sell_sum < -LIMIT:
                                volume = -LIMIT - curr_pos - sell_sum
                            if volume < 0:
                                if volume + sell_sum + curr_pos < -LIMIT:
                                    raise RuntimeError()
                                sell_sum = sell_sum + volume
                                orders.append(Order(product, bid, volume))
                spread = 2

                if len(order_depth.sell_orders) > 0 and len(order_depth.buy_orders) > 0:
                    asks = list(order_depth.sell_orders.keys())
                    asks.sort()
                    bids = list(order_depth.buy_orders.keys())
                    bids.sort(reverse=True)
                    spread = abs(asks[0]-bids[0])/10

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

                # CURRENT BEST
                k1 = 3  # default spread size

                q_s = sum(order_depth.sell_orders.values())
                q_b = sum(order_depth.buy_orders.values())

                avg_s = sum([order_depth.sell_orders[key] *
                            key for key in order_depth.sell_orders.keys()])/sum(order_dept.sell_orders.values())
                avg_b = sum([order_depth.buy_orders[key] *
                            key for key in order_depth.buy_orders.keys()])/sum(order_depth.buy_orders.values())

                # TEST
                # k1 = (avg_s-avg_b)*0.9

                # average bid/ask method
                p_t = (avg_s+avg_b)/2

                # price_sum = 0
                # qt = 0
                # if product in state.market_trades.keys():
                #     for trade in state.market_trades[product]:
                #         price_sum += trade.quantity*trade.price
                #         qt += trade.quantity
                #     if qt != 0 and qt > 7:
                #         p_t = price_sum/qt

                # Excessive buy
                # if q_b + q_s == 0:
                #     bid_price = p_t - k1/2
                #     ask_price = p_t + k1/2

                # elif (q_s-q_b)/(q_b+q_s) > 0.5:
                #     bid_price = p_t
                #     ask_price = p_t + k1

                # # Excessive sell
                # elif (q_b-q_s)/(q_b+q_s) > 0.5:
                #     bid_price = p_t - k1
                #     ask_price = p_t
                # # Passive
                # else:
                #     bid_price = p_t - k1/2
                #     ask_price = p_t + k1/2

                bid_price = p_t - k1/2
                ask_price = p_t + k1/2

                orders.append(Order(product, bid_price, LIMIT - curr_pos))
                orders.append(Order(product, ask_price, -curr_pos - LIMIT))

                result[product] = orders
        # self.__filter(state, result)
        # self.__print_result(result)
        # self.__print_own_trades(state.own_trades)
        logger.flush(state, result)
        return result

    def __filter(self, state: TradingState, result: Dict[str, List[Order]], limit=20):
        for product in result.keys():
            sum = 0
            curr_pos = 0
            if product in state.position.keys():
                curr_pos = state.position[product]

            for order in result[product]:
                sum += order.quantity

            if abs(sum + curr_pos) > limit:
                for idx, order in enumerate(result[product]):
                    if (order.quantity > 0):
                        result[product][idx] = Order(
                            product, order.price, math.floor(order.quantity*limit/abs(sum + curr_pos)))
                    else:
                        result[product][idx] = Order(
                            product, order.price, math.ceil(order.quantity*limit/abs(sum + curr_pos)))
