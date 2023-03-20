from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
import statistics
import math

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        products = self.__availableProducts(state.order_depths)

        estimated_price = {}
        result = {}

        for product in products:
            orders: list[Order] = []
            if product not in state.market_trades.keys():
                continue
            spread = self.__spread(state.order_depths[product])
            fair_price = self.__meanTradedPrice(state.market_trades[product])
            if fair_price != -1:
                self.__fair_price_method(
                    state, orders, fair_price-spread/2, fair_price+spread/2, product)

            result[product] = orders

        self.__filter(state, result)
        self.__print_result(result)
        return result

    def __print_result(self, result):
        for product in result.keys():
            for order in result[product]:
                if order.quantity > 0:
                    print(f"BUY {product} {order.quantity} @ {order.price}")
                elif order.quantity < 0:
                    print(f"SELL {product} {-order.quantity} @ {order.price}")

    # 0 : price, 1 : volume (positive)
    def __min_ask(self, order_depth):
        ma = min(order_depth.sell_orders.keys())
        return (ma, -order_depth.sell_orders[ma])

    # 0 : price, 1 : volume (positive)
    def __max_bid(self, order_depth):
        mb = max(order_depth.buy_orders.keys())
        return (mb, order_depth.buy_orders[mb])

    def __availableProducts(self, order_depths):
        return order_depths.keys()

    def __meanTradedPrice(self, trades, method=statistics.mean):
        list = []
        for trade in trades:
            for quantity in range(trade.quantity):
                list.append(trade.price)

        if not list:
            return -1
        return method(list)

    def __filter(self, state: TradingState, result: Dict[str, List[Order]], limit=19):
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

    def __spread(self, order_depth, method=statistics.mean, param=1):
        asks = []
        bids = []

        for price in order_depth.sell_orders.keys():
            for i in range(order_depth.sell_orders[price]):
                asks.append(price)

        for price in order_depth.buy_orders.keys():
            for i in range(order_depth.buy_orders[price]):
                bids.append(price)

        if not asks or not bids:
            return 0

        avg_ask = method(asks)
        avg_bid = method(bids)
        return (avg_ask - avg_bid) * param

    def __fair_price_method(self, state: TradingState, orders, bid, ask, product):
        min_ask = self.__min_ask(state.order_depths[product])
        max_bid = self.__max_bid(state.order_depths[product])

        if min_ask[0] < bid:
            orders.append(Order(product, min_ask[0], min_ask[1]))
        if max_bid[0] > ask:
            orders.append(Order(product, max_bid[0], -max_bid[1]))
