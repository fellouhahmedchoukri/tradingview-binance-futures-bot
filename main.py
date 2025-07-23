from flask import Flask, request, jsonify
import os
import binance
from binance.client import Client
import logging
from logging.handlers import RotatingFileHandler

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
log_handler = RotatingFileHandler(
    'grid_bot.log', 
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3
)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

@app.route('/', methods=['GET'])
def home():
    return "✅ Grid Trading Bot - Active and Ready"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    logger.info(f"[📥 Webhook received] : {data}")

    # Vérification de sécurité
    if passphrase != "default-passphrase" and data.get('passphrase') != passphrase:
        logger.warning("Unauthorized access attempt")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        # Nouveau format de message structuré
        if 'message' in data:
            message = data['message']
            parts = message.split('|')
            
            # Traitement GRID_ENTRY
            if len(parts) >= 4 and parts[0] == "GRID_ENTRY":
                return handle_grid_entry(parts)
            
            # Traitement GRID_EXIT
            elif len(parts) >= 3 and parts[0] == "GRID_EXIT":
                return handle_grid_exit(parts)
        
        # Ancien format pour compatibilité
        action = data.get('action')
        if action == "grid_entry":
            return handle_legacy_grid_entry(data)
        
        return jsonify({
            "status": "error", 
            "message": "Unknown action or message format"
        }), 400

    except binance.exceptions.BinanceAPIException as api_error:
        error_msg = f"Binance API Error: {api_error.code} - {api_error.message}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "code": api_error.code,
            "message": error_msg
        }), 400
        
    except binance.exceptions.BinanceOrderException as order_error:
        error_msg = f"Order Error: {order_error.message}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 400
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error", 
            "message": error_msg
        }), 500

def handle_grid_entry(parts):
    """Traite les entrées de grille au nouveau format"""
    symbol = parts[1]
    lot_size = float(parts[2])
    levels = parts[3].split(',')
    
    logger.info(f"Placing grid for {symbol} with lots: {lot_size} at levels: {levels}")
    
    orders = []
    for price in levels:
        try:
            # Convertir en float et arrondir à 2 décimales
            price_value = round(float(price), 2)
            
            order = client.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="LIMIT",
                quantity=lot_size,
                price=price_value,
                timeInForce="GTC"
            )
            orders.append(order)
            logger.info(f"Order placed: {order}")
            
        except binance.exceptions.BinanceAPIException as e:
            if e.code == -2010:  # Ordre en dessous du minimum
                logger.warning(f"Price too low, adjusting: {price}")
                # Ajuster le prix en augmentant de 1%
                adjusted_price = round(float(price) * 1.01, 2)
                
                order = client.futures_create_order(
                    symbol=symbol,
                    side="BUY",
                    type="LIMIT",
                    quantity=lot_size,
                    price=adjusted_price,
                    timeInForce="GTC"
                )
                orders.append(order)
                logger.info(f"Adjusted order placed at {adjusted_price}")
            else:
                # Si c'est une autre erreur, on la propage
                logger.error(f"Error placing order: {e}")
                raise e
    
    logger.info(f"✅ Grid orders placed: {len(orders)} orders")
    return jsonify({
        "status": "success", 
        "orders": orders,
        "message": f"Grid placed with {len(orders)} orders"
    }), 200

def handle_grid_exit(parts):
    """Traite les sorties de grille (TP/SL)"""
    symbol = parts[1]
    reason = parts[2]
    price = parts[3] if len(parts) > 3 else "N/A"
    
    logger.info(f"Closing grid for {symbol} ({reason} at {price})")
    
    # Annulation de tous les ordres
    cancel_response = client.futures_cancel_all_orders(symbol=symbol)
    logger.info(f"Orders canceled: {cancel_response}")
    
    # Fermeture des positions
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
                close_orders.append(close_order)
                logger.info(f"Position closed: {close_order}")
                
            except binance.exceptions.BinanceAPIException as e:
                logger.error(f"Error closing position: {e}")
    
    logger.info(f"✅ Grid closed: {len(close_orders)} positions closed")
    return jsonify({
        "status": "success", 
        "action": "close_all",
        "reason": reason,
        "closed_positions": close_orders
    }), 200

def handle_legacy_grid_entry(data):
    """Ancien format pour compatibilité"""
    symbol = data['symbol']
    lot_size = float(data['lot_size'])
    grid_levels = data['grid_levels']
    
    orders = []
    for level in grid_levels:
        # Convertir en float et arrondir à 2 décimales
        price_value = round(float(level), 2)
        
        order = client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="LIMIT",
            quantity=lot_size,
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
