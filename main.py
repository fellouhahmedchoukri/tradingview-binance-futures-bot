from flask import Flask, request, jsonify
import os
from binance.client import Client

app = Flask(__name__)

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"

client = Client(api_key, api_secret, testnet=testnet)

@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Binance Futures actif."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("[📥 Webhook reçu] :", data)

    try:
        action = data.get('action')

        if action == "grid_entry":
            symbol = data['symbol']
            lot_size = float(data['lot_size'])
            grid_levels = data['grid_levels']

            # Exemple : placer des BUY LIMIT à chaque niveau de grille
            orders = []
            for level in grid_levels:
                order = client.futures_create_order(
                    symbol=symbol,
                    side="BUY",
                    type="LIMIT",
                    quantity=lot_size,
                    price=round(float(level), 2),
                    timeInForce="GTC"
                )
                orders.append(order)

            print("✅ Ordres placés :", orders)
            return jsonify({"status": "success", "orders": orders}), 200

        else:
            return jsonify({"status": "error", "message": f"Action inconnue : {action}"}), 400

    except Exception as e:
        print("❌ Erreur :", e)
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
