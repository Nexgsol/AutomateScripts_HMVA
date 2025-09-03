import os, io, json, requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def _drive():
    sa_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON","")
    if not sa_json:
        raise RuntimeError("GDRIVE_SERVICE_ACCOUNT_JSON not set (service account JSON string).")
    info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive.file"])
    return build("drive","v3", credentials=creds, cache_discovery=False)

def upload_from_url(url: str, file_name: str, folder_id: str):
    dr = _drive()
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    bio = io.BytesIO(r.content)
    media = MediaIoBaseUpload(bio, mimetype="video/mp4", resumable=True)
    file_metadata = {"name": file_name}
    if folder_id: file_metadata["parents"] = [folder_id]
    f = dr.files().create(body=file_metadata, media_body=media, fields="id, webViewLink, webContentLink").execute()
    return f
