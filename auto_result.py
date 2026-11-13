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

        # GitHub run thoda jaldi ya late ho sakta hai
    # Nearest 30-minute slot choose karo
    minute_of_day = now.hour * 60 + now.minute
    slot_total = ((minute_of_day + 5) // 30) * 30

    if not (600 <= slot_total <= 1260):
        print("Scheduled time ke bahar.")
        return

    slot = now.replace(
        hour=slot_total // 60,
        minute=slot_total % 60,
        second=0,
        microsecond=0
    )

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
