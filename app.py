from flask import Flask, jsonify,request
import os, json, firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from flask_cors import CORS
import requests

# Initialize Flask app
app = Flask(__name__)
CORS(app) 


TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"


# Initialize Firebase
firebase_creds = json.loads(os.environ["FIREBASE_CREDS"])
cred = credentials.Certificate(firebase_creds)
# cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/",methods=["GET","HEAD"])
def home():
    print("Ping received at:", datetime.now())
    return jsonify({"status": "Backend is running"}),200



@app.route("/registerUser", methods=["POST"])
def register_user():
    data = request.get_json()
    print("Received data:", data)

    if not data:
        return jsonify({"error": "No data received"}), 400

    uid = data.get("uid")
    username = data.get("username")
    email = data.get("email")

    if not uid or not username:
        return jsonify({"error": "uid and username are required"}), 400

    try:
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if user_doc.exists:
            return jsonify({"message": "User already registered"}), 200
        else:
            new_user = {"uid": uid,"username": username,"email": email,"chatId": None,"createdAt": datetime.utcnow().isoformat()}
            user_ref.set(new_user)
            return jsonify({"message": "User registered successfully","user": new_user}), 201
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
    


    
@app.route("/getUser", methods=["GET"])
def get_user():
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"error": "uid is required"}), 400

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if user_doc.exists:
        return jsonify(user_doc.to_dict()), 200
    else:
        return jsonify({"error": "User not found"}), 404



# @app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
@app.route(f"/webhook/{os.environ['TELEGRAM_BOT_TOKEN']}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("Got update:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if text.startswith("/start"):
            parts = text.split(" ", 1)
            if len(parts) == 2:
                uid = parts[1] 
                
                user_ref = db.collection("users").document(uid)
                user_doc = user_ref.get()

                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    username = user_data.get("username", "Unknown User")

                    # update chatId in Firestore
                    user_ref.update({"chatId": chat_id})
                    print(f"✅ Updated chatId for user {uid} = {chat_id}")

                    # send actual message via Telegram API
                    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Account linked with username: {username}"
                    })

    return "OK", 200

















# @app.route("/add_sample")
# def add_sample():
    
#     doc_ref = db.collection("samples").document()
#     doc_ref.set({
#         "message": "Hello from Flask & Firebase!",
#         "timestamp": datetime.now()
#     })
#     return jsonify({"status": "Document added"})


# @app.route("/get_samples")
# def get_samples():
#     docs = db.collection("samples").stream()
#     data = [{doc.id: doc.to_dict()} for doc in docs]
#     return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
