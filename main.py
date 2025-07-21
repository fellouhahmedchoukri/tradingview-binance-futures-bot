from flask import Flask, request, jsonify
from binance.client import Client
import os
from datetime import datetime  # Pour journalisation horodatée

# 🧠 Flask instance
app = Flask(__name__)

# 🔑 Récupération des clés API et du mode Testnet depuis les variables Railway
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "False") == "True"

# 📦 Création du client Binance (testnet ou réel)
client = Client(api_key, api_secret, testnet=testnet)

# ✅ Route de test (GET)
@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Binance Futures actif."

# 🎯 Route Webhook (POST depuis TradingView)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    # 🕒 Affiche la requête reçue avec horodatage
    print(f"[{datetime.now()}] 📥 Webhook reçu : {data}")

    try:
        symbol = data['symbol']
        side = data['side'].upper()  # 'BUY' ou 'SELL'
        quantity = float(data['amount'])  # Ex : 0.01
        order_type = data.get('type', 'MARKET').upper()  # Par défaut: MARKET
        price = float(data['price']) if 'price' in data else None

        # 🧾 Construction des paramètres d’ordre
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
        }
        if order_type == "LIMIT":
            params['price'] = price
            params['timeInForce'] = "GTC"

        # ✅ Envoi de l'ordre
        order = client.futures_create_order(**params)
        print("✅ Ordre exécuté :", order)
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print("❌ Erreur :", e)
        return jsonify({"status": "error", "message": str(e)}), 400

# ▶️ Lancement de l'application Flask (Railway détecte le port automatiquement)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
