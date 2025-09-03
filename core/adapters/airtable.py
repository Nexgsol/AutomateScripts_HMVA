import os, requests
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN","")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID","")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE","Requests")

def push_record(fields: dict) -> str:
    if not (AIRTABLE_TOKEN and AIRTABLE_BASE_ID):
        return "airtable_stub"
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
    r = requests.post(url, headers={"Authorization":f"Bearer {AIRTABLE_TOKEN}","Content-Type":"application/json"},
                      json={"fields": fields}, timeout=60)
    r.raise_for_status()
    return r.json().get("id","")
