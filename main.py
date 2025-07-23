from flask import Flask, request, jsonify
import os
from binance.client import Client

app = Flask(__name__)

# 🔑 Clés d'API Binance
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"

client = Client(api_key, api_secret, testnet=testnet)

@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Binance Futures actif."

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.content_type != 'application/json':
        return 'Unsupported Media Type', 415

    data = request.get_json()
    print("[📥 Webhook reçu] :", data)

    try:
        action = data.get('action')

        if action == "grid_entry":
            symbol = data['symbol']
            lot_size = float(data['lot_size'])
            grid_levels = data['grid_levels']

            orders = []
            for level in grid_levels:
                order = client.futures_create_order(
                    symbol=symbol,
                    side="BUY",  # Peut être rendu dynamique
                    type="LIMIT",
                    price=str(level),
                    quantity=lot_size,
                    timeInForce="GTC"
                )
                orders.append(order)

            return jsonify({'status': 'orders placed', 'details': orders}), 200

        else:
            return jsonify({'error': 'Invalid action'}), 400

    except Exception as e:
        print("[❌ Erreur webhook] :", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
