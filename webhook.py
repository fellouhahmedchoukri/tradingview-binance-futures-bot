# fichier : webhook.py (extrait modifié pour gérer plusieurs stratégies)

from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    print(f"[📥 Webhook reçu] : {data}")

    strategy = data.get("strategy")

    if not strategy:
        return "Strategy name is missing", 400

    # Routage selon la stratégie
    if strategy == "GRID-BOT":
        return handle_grid_bot(data)
    elif strategy == "FUTURES-BOT":
        return handle_futures_bot(data)
    else:
        return f"Stratégie inconnue : {strategy}", 400


def handle_grid_bot(data):
    # Exemple de traitement (à adapter à ta logique GRID)
    symbol = data.get("symbol")
    side = data.get("side")
    price = data.get("price")
    time = data.get("time")

    print(f"[GRID-BOT] {time} | {symbol} | {side.upper()} @ {price}")
    # ➕ Ajouter ici la logique d’envoi à Binance spot ou futures
    return "Order processed for GRID-BOT", 200


def handle_futures_bot(data):
    # Exemple de traitement (à adapter à ta logique FUTURES)
    symbol = data.get("symbol")
    side = data.get("side")
    price = data.get("price")
    time = data.get("time")

    print(f"[FUTURES-BOT] {time} | {symbol} | {side.upper()} @ {price}")
    # ➕ Ajouter ici la logique d’envoi à Binance Futures
    return "Order processed for FUTURES-BOT", 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
