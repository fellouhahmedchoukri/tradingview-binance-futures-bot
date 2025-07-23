from flask import Flask, request, jsonify
import os
import binance
from binance.client import Client
import logging
from logging.handlers import RotatingFileHandler
import json

app = Flask(__name__)

# 🔑 Configuration initiale
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"
passphrase = os.getenv("WEBHOOK_PASSPHRASE", "default-passphrase")

# Initialisation du client Binance
client = Client(api_key, api_secret, testnet=testnet)

# 🔐 Configuration du logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('grid_bot.log', maxBytes=5*1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

@app.route('/', methods=['GET'])
def home():
    return "✅ Grid Trading Bot - Active and Ready"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 🔍 Log brut du payload reçu
        raw_data = request.data.decode('utf-8')
        logger.info(f"[📥 RAW Webhook Payload] : {raw_data}")
        data = json.loads(raw_data)
    except Exception as e:
        logger.error(f"[❌ ERROR decoding JSON] : {e}")
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400

    logger.info(f"[📥 Parsed Webhook JSON] : {data}")

    if passphrase != "default-passphrase" and data.get('passphrase') != passphrase:
        logger.warning("Unauthorized access attempt")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        if 'message' in data:
            message = data['message']
            parts = message.split('|')

            if len(parts) >= 4 and parts[0] == "GRID_ENTRY":
                return handle_grid_entry(parts)
            elif len(parts) >= 3 and parts[0] == "GRID_EXIT":
                return handle_grid_exit(parts)

        action = data.get('action')
        if action == "grid_entry":
            return handle_legacy_grid_entry(data)

        return jsonify({"status": "error", "message": "Unknown action or message format"}), 400

    except binance.error.ClientError as api_error:
        logger.error(f"Binance API Error: {api_error}")
        return jsonify({"status": "error", "message": str(api_error)}), 400

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ Fonction d'arrondi selon les filtres de Binance
def get_symbol_filters(symbol):
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == symbol:
            return s['filters']
    return []

def format_quantity_price(symbol, quantity, price):
    filters = get_symbol_filters(symbol)
    step_size = tick_size = None

    for f in filters:
        if f['filterType'] == 'LOT_SIZE':
            step_size = float(f['stepSize'])
        elif f['filterType'] == 'PRICE_FILTER':
            tick_size = float(f['tickSize'])

    if step_size:
        quantity = quantity - (quantity % step_size)
    if tick_size:
        price = price - (price % tick_size)

    return round(quantity, 8), round(price, 8)

# 🚀 Entrée GRID
def handle_grid_entry(parts):
    symbol = parts[1].upper()
    lot_size = float(parts[2])
    levels = parts[3].split(',')

    logger.info(f"Placing grid for {symbol} with lots: {lot_size} at levels: {levels}")

    orders = []
    for price in levels:
        try:
            quantity, price_value = format_quantity_price(symbol, lot_size, float(price))
            order = client.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="LIMIT",
                quantity=quantity,
                price=price_value,
                timeInForce="GTC"
            )
            orders.append(order)
            logger.info(f"Order placed: {order}")

        except binance.error.ClientError as e:
            if "MIN_NOTIONAL" in str(e):
                logger.warning(f"Price too low, adjusting: {price}")
                adjusted_price = float(price) * 1.01
                quantity, price_value = format_quantity_price(symbol, lot_size, adjusted_price)
                order = client.futures_create_order(
                    symbol=symbol,
                    side="BUY",
                    type="LIMIT",
                    quantity=quantity,
                    price=price_value,
                    timeInForce="GTC"
                )
                orders.append(order)
                logger.info(f"Adjusted order placed at {price_value}")
            else:
                raise e

    logger.info(f"✅ Grid orders placed: {len(orders)} orders")
    return jsonify({"status": "success", "orders": orders}), 200

# 🚪 Sortie GRID
def handle_grid_exit(parts):
    symbol = parts[1].upper()
    reason = parts[2]
    price = parts[3] if len(parts) > 3 else "N/A"

    logger.info(f"Closing grid for {symbol} ({reason} at {price})")

    cancel_response = client.futures_cancel_all_orders(symbol=symbol)
    logger.info(f"Orders canceled: {cancel_response}")

    positions = client.futures_position_information(symbol=symbol)
    close_orders = []

    for pos in positions:
        position_amt = float(pos['positionAmt'])
        if position_amt != 0:
            side = "SELL" if position_amt > 0 else "BUY"
            try:
                close_order = client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=abs(position_amt)
                )
                close_orders.append(close_order)
                logger.info(f"Position closed: {close_order}")
            except binance.error.ClientError as e:
                logger.error(f"Error closing position: {e}")

    logger.info(f"✅ Grid closed: {len(close_orders)} positions closed")
    return jsonify({"status": "success", "closed_positions": close_orders}), 200

# 🧩 Ancienne version (legacy)
def handle_legacy_grid_entry(data):
    symbol = data['symbol'].upper()
    lot_size = float(data['lot_size'])
    grid_levels = data['grid_levels']

    orders = []
    for level in grid_levels:
        quantity, price_value = format_quantity_price(symbol, lot_size, float(level))
        order = client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="LIMIT",
            quantity=quantity,
            price=price_value,
            timeInForce="GTC"
        )
        orders.append(order)
        logger.info(f"Legacy order placed: {order}")

    logger.info(f"✅ Legacy grid placed: {len(orders)} orders")
    return jsonify({"status": "success", "orders": orders}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Starting Grid Trading Bot on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
