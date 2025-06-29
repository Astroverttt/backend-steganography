import requests
import hashlib
import hmac
import json

ORDER_ID = "ORDER-30313c7d-11ae-4322-a86b-c4bd72f3a57e"  
STATUS_CODE = "200"
GROSS_AMOUNT = "100000"
SERVER_KEY = "SB-Mid-server-h0ioErmlY553Kp2KMHS_FRGF" 

CALLBACK_URL = "https://b454-114-10-44-160.ngrok-free.app/payments/payment-callback"

input_string = ORDER_ID + STATUS_CODE + GROSS_AMOUNT + SERVER_KEY
signature_key = hmac.new(
    SERVER_KEY.encode(), input_string.encode(), hashlib.sha512
).hexdigest()

payload = {
    "order_id": ORDER_ID,
    "status_code": STATUS_CODE,
    "gross_amount": GROSS_AMOUNT,
    "signature_key": signature_key,
    "transaction_status": "settlement",
    "customer_details": {
        "email": "rossi@yopmail.com"  
    },
    "item_details": [
        {
            "id": "e666dd86-b7e1-4976-875c-04448e1caf05" 
        }
    ]
}

headers = {"Content-Type": "application/json"}
response = requests.post(CALLBACK_URL, headers=headers, json=payload)
# Tampilkan hasil
print("Status:", response.status_code)
print("Response:", response.text)
