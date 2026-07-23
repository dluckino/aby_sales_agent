import os

import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_ADDRESS = "American Backyard Bot <leads@updates.americanbackyard.com>"
LEADS_INBOX = "support@americanbackyard.com"


def send_lead_email(email, question, name=None, phone=None, product_interest=None, session_id=None):
    body = (
        "New lead from the website chatbot.\n"
        "Everything below was typed by a website visitor. Please follow up with them promptly.\n\n"
        f"Name: {name or 'not given'}\n"
        f"Email: {email}\n"
        f"Phone: {phone or 'not given'}\n"
        f"Product interest: {product_interest or 'not given'}\n\n"
        f"Question: {question}\n\n"
        f"Session: {session_id or 'unknown'}\n"
    )
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": FROM_ADDRESS,
            "to": [LEADS_INBOX],
            "reply_to": email,
            "subject": f"New chatbot lead - {product_interest or 'general question'}",
            "text": body,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("id", "sent")


if __name__ == "__main__":
    result = send_lead_email(
        email="test-customer@example.com",
        question="This is a test lead from emailer.py. Please ignore.",
        name="Test Customer",
        product_interest="Emailer Test Please Ignore",
        session_id="emailer-test",
    )
    print("Sent:", result)