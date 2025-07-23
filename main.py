from flask import Flask, request, jsonify
import os
from binance.client import Client
import json

app = Flask(__name__)

# 🔑 Clés d'API Binance
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"

client = Client(api_key, api_secret, testnet=testnet)

@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Binance Futures actif."

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "✅ Webhook alive (GET)", 200

    # POST handling
    # Log brut du payload
    raw = request.data.decode('utf-8')
    print(f"[📥 RAW Webhook Payload] : {raw}")
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"[❌ ERROR decoding JSON] : {e}")
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400

    print(f"[📥 Parsed Webhook JSON] : {data}")
    try:
        action = data.get('action')

        if action == "grid_entry":
            symbol = data['symbol']
            lot_size = float(data['lot_size'])
            grid_levels = data['grid_levels']

            orders = []
            for level in grid_levels:
                price = round(float(level), 2)
                order = client.futures_create_order(
                    symbol=symbol,
                    side="BUY",  # Tu peux rendre ça dynamique plus tard
                    type="LIMIT",
                    quantity=lot_size,
                    price=price,
                    timeInForce="GTC"
                )
                orders.append(order)

            print("✅ Ordres LIMIT placés :", orders)
            return jsonify({"status": "success", "orders": orders}), 200

        else:
            return jsonify({"status": "error", "message": f"Action inconnue : {action}"}), 400

    except Exception as e:
        print("❌ Erreur :", e)
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Pour plus de visibilité en local, debug=True
    app.run(host="0.0.0.0", port=port, debug=True)
