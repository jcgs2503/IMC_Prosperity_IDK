from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import math


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
                if len(order_depth.sell_orders) > 0:
                    asks = list(order_depth.sell_orders.keys())
                    asks.sort()
                    for ask in asks:
                        if ask < acceptable_price:
                            volume = -order_depth.sell_orders[ask]
                            if volume + curr_pos > LIMIT:
                                volume = LIMIT - curr_pos
                            if volume != 0:
                                orders.append(Order(product, ask, volume))

                if len(order_depth.buy_orders) != 0:
                    bids = list(order_depth.buy_orders.keys())
                    bids.sort(reverse=True)
                    for bid in bids:
                        if bid > acceptable_price:
                            volume = -order_depth.buy_orders[bid]
                            if volume + curr_pos < -LIMIT:
                                volume = -LIMIT - curr_pos
                            if volume != 0:
                                orders.append(Order(product, bid, volume))

                result[product] = orders

            # if product == 'BANANAS':
            #     LIMIT = 20
            #     order_depth: OrderDepth = state.order_depths[product]
            #     orders: list[Order] = []

            #     order_bias = sum(order_depth.sell_orders) + \
            #         sum(order_depth.buy_orders)
            #     if order_bias > 0:
            #         asks = list(order_depth.sell_orders.keys())
            #         asks.sort()
            #         for ask in asks:
            #             volume = -order_depth.sell_orders[ask]
            #             if volume + curr_pos > LIMIT:
            #                 volume = LIMIT - curr_pos
            #             if volume != 0:
            #                 orders.append(Order(product, ask, volume))
            #     elif order_bias < 0:
            #         bids = list(order_depth.buy_orders.keys())
            #         bids.sort(reverse=True)
            #         for bid in bids:
            #             volume = -order_depth.buy_orders[bid]
            #             if volume + curr_pos < -LIMIT:
            #                 volume = -LIMIT - curr_pos
            #             if volume != 0:
            #                 orders.append(Order(product, bid, volume))
            #     else:
            #         mid_price = (min(order_depth.sell_orders.keys()) +
            #                      max(order_depth.buy_orders.keys()))/2.0
            #         orders.append(Order(product, mid_price, -curr_pos))

            #     result[product] = orders
        # self.__filter(state, result)
        self.__print_result(result)
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

    def __print_result(self, result):
        for product in result.keys():
            for order in result[product]:
                if order.quantity > 0:
                    print(f"BUY {product} {order.quantity} @ {order.price}")
                elif order.quantity < 0:
                    print(f"SELL {product} {-order.quantity} @ {order.price}")
