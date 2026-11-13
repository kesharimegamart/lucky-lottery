
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import firebase_admin
from firebase_admin import credentials, firestore

# India time
IST = ZoneInfo("Asia/Kolkata")

# Firebase service account key GitHub Secret se milegi
import json
service_account = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def main():
    now = datetime.now(IST)

    # AUTO mode check
    mode_doc = db.collection("settings").document("mode").get()

    if not mode_doc.exists:
        print("Settings mode document nahi mila.")
        return

    mode = mode_doc.to_dict().get("mode", "").upper()

    if mode != "AUTO":
        print("AUTO mode active nahi hai.")
        return

    # 10:00 AM se 9:00 PM tak 30-minute slots
    start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    end = now.replace(hour=21, minute=0, second=0, microsecond=0)

    if now < start or now > end:
        print("Abhi result ka scheduled time nahi hai.")
        return

    slot_minute = 0 if now.minute < 30 else 30
    slot = now.replace(
        minute=slot_minute, second=0, microsecond=0
    )

    if now < slot:
        print("Slot abhi nahi aaya.")
        return

    date_text = slot.strftime("%Y-%m-%d")
    time_text = slot.strftime("%I:%M %p")

    doc_id = slot.strftime("%Y-%m-%d_%H-%M")
    result_ref = db.collection("results").document(doc_id)

    if result_ref.get().exists:
        print("Is slot ka result pehle se maujood hai.")
        return

    number = f"{random.randint(0, 999):03d}"

    result_ref.set({
        "date": date_text,
        "time": time_text,
        "number": number,
        "publishAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

    print(f"Result saved: {time_text} = {number}")

if __name__ == "__main__":
    main()
