import os
import json
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import firebase_admin
from firebase_admin import credentials, firestore

IST = ZoneInfo("Asia/Kolkata")

service_account = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred)

db = firestore.client()


def main():
    now = datetime.now(IST)

    # Sirf 10 AM se 9 PM tak
    if not (10 <= now.hour <= 21):
        print("Scheduled time ke bahar.")
        return

    # Har ghante :00 aur :30 slot
    if now.minute <= 14:
        minute = 0
    elif 30 <= now.minute <= 44:
        minute = 30
    else:
        print("Scheduled slot nahi hai.")
        return

    slot = now.replace(minute=minute, second=0, microsecond=0)

    # Admin ka AUTO/MANUAL mode
    mode_doc = db.collection("settings").document("automation").get()

    if not mode_doc.exists:
        print("Automation settings nahi mili.")
        return

    mode = mode_doc.to_dict().get("mode", "manual").lower()

    if mode != "auto":
        print("AUTO mode active nahi hai.")
        return

    date_text = slot.strftime("%Y-%m-%d")
    time_text = slot.strftime("%H:%M")
    doc_id = f"{date_text}_{time_text.replace(':', '-')}"

    result_ref = db.collection("demo_results").document(doc_id)

    if result_ref.get().exists:
        print("Is slot ka demo number pehle se hai.")
        return

    number = f"{random.SystemRandom().randrange(1000):03d}"

    result_ref.create({
        "date": date_text,
        "time": time_text,
        "number": number,
        "publishAt": slot.astimezone(timezone.utc),
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "source": "random_demo"
    })

    print(f"Random demo number saved: {time_text} = {number}")


if __name__ == "__main__":
    main()
