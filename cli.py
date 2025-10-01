"""
cli.py
Small CLI wrapper to place orders via BasicBot.
"""

import os
import argparse
from bot import BasicBot, logger

def positive_float(v):
    try:
        f = float(v)
    except:
        raise argparse.ArgumentTypeError("Must be a number")
    if f <= 0:
        raise argparse.ArgumentTypeError("Must be positive")
    return f

def main():
    parser = argparse.ArgumentParser(description="Simplified Binance Futures Testnet Trading Bot (CLI)")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g. BTCUSDT)")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--type", required=True, choices=["MARKET", "LIMIT", "STOPLIMIT"], help="Order type")
    parser.add_argument("--quantity", required=True, type=positive_float, help="Quantity (in contract/lot decimal)")
    parser.add_argument("--price", type=positive_float, help="Price for LIMIT order")
    parser.add_argument("--stop-price", dest="stop_price", type=positive_float, help="Stop price for STOPLIMIT")
    parser.add_argument("--time-in-force", dest="tif", default="GTC", choices=["GTC","IOC","FOK"], help="Time in force for LIMIT")
    args = parser.parse_args()

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        logger.error("API credentials not found in environment variables.")
        parser.exit(1)

    bot = BasicBot(api_key, api_secret)

    try:
        if args.type == "MARKET":
            res = bot.place_market_order(args.symbol, args.side, args.quantity)
        elif args.type == "LIMIT":
            if not args.price:
                logger.error("LIMIT order requires --price")
                parser.exit(1)
            res = bot.place_limit_order(args.symbol, args.side, args.quantity, args.price, time_in_force=args.tif)
        elif args.type == "STOPLIMIT":
            if not args.stop_price or not args.price:
                logger.error("STOPLIMIT requires --stop-price and --price")
                parser.exit(1)
            res = bot.place_stop_limit_order(args.symbol, args.side, args.quantity, args.stop_price, args.price, time_in_force=args.tif)
        else:
            logger.error("Unknown order type")
            parser.exit(1)

        # Print a short summary to stdout and log details
        logger.info("Order response: %s", res)
        print("Order placed. Response snippet:")
        # show a compact result for the user
        keys = ["symbol","orderId","status","avgPrice","price","origQty","executedQty","side","type"]
        for k in keys:
            if k in res:
                print(f"{k}: {res[k]}")
    except Exception as e:
        logger.exception("Order failed: %s", e)
        parser.exit(2)

if __name__ == "__main__":
    main()
