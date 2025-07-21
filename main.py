from flask import Flask, request, jsonify
import os
from binance.client import Client

# 🧠 Flask instance (obligatoire)
app = Flask(__name__)

# 🔑 Clés API depuis les variables Railway
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"

# 📦 Client Binance
client = Client(api_key, api_secret, testnet=testnet)

# ✅ Route principale
@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Binance Futures actif."

# 🎯 Route Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook reçu:", data)

    try:
        symbol = data['symbol']
        side = data['side'].upper()
        quantity = float(data['amount'])
        order_type = data.get('type', 'MARKET').upper()
        price = float(data['price']) if 'price' in data else None

        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
        }
        if order_type == "LIMIT":
            params['price'] = price
            params['timeInForce'] = "GTC"

        order = client.futures_create_order(**params)
        print("Ordre exécuté :", order)
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print("Erreur :", e)
        return jsonify({"status": "error", "message": str(e)}), 400

# ▶️ Lancement app (Railway lit PORT)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
