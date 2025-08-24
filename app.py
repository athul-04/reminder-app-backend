from flask import Flask, jsonify,request
import os, json, firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from flask_cors import CORS
from firebase_admin import auth
import requests


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["*"]}}, supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


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



@app.route("/addReminder", methods=["POST"])
def add_reminder():
    data = request.get_json()

    id_token = request.headers.get("Authorization")  # frontend sends Bearer token
    if not id_token:
        return jsonify({"error": "Missing auth token"}), 401

    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(id_token.replace("Bearer ", ""))
        uid = decoded_token["uid"]
    except Exception as e:
        return jsonify({"error": "Invalid token", "details": str(e)}), 401

    title = data.get("title")
    body = data.get("body")
    timestamp = data.get("timestamp")

    if not title or not body or not timestamp:
        return jsonify({"error": "title, body and timestamp are required"}), 400

    reminder_ref = db.collection("reminders").document()
    reminder = {
        "uid": uid,   # ✅ take from verified token
        "title": title,
        "body": body,
        "timestamp": timestamp,
        "createdAt": datetime.utcnow().isoformat()
    }
    reminder_ref.set(reminder)

    return jsonify({"message": "Reminder added successfully", "reminder": reminder}), 201

@app.route("/getReminders", methods=["GET"])
def get_reminders():
    try:
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        token = auth_header.split(" ")[1]  # "Bearer <token>"

        # Verify Firebase token
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]

        # Fetch reminders from Firestore
        reminders_ref = db.collection("reminders").where("uid", "==", uid)
        reminders = [doc.to_dict() | {"id": doc.id} for doc in reminders_ref.stream()]

        return jsonify(reminders), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)














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


