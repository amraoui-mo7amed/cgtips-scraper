import logging
import os
import pickle
import random
import re
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

logger = logging.getLogger("gdrive_api")

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"


def _get_service():
    if not os.path.exists(CREDENTIALS_FILE):
        logger.warning("credentials.json not found — Drive API unavailable")
        return None

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        except Exception as e:
            logger.error("OAuth flow failed: %s", e)
            return None
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("drive", "v3", credentials=creds)


def _sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" .") or "download"


def _exec_with_retry(request_fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            return request_fn()
        except HttpError as e:
            status = e.resp.status
            reason = str(e).lower()
            if status == 403 and ("rateLimit" in reason or "limit" in reason):
                if attempt == max_retries - 1:
                    raise
                delay = (3 ** attempt) + random.uniform(0, 2)
                logger.warning("API rate limited, retrying in %ds (attempt %d/%d)", int(delay), attempt + 1, max_retries)
                time.sleep(delay)
            else:
                raise


def copy_and_download(file_id, dest_path):
    service = _get_service()
    if service is None:
        return None

    try:
        orig = _exec_with_retry(lambda: service.files().get(
            fileId=file_id, fields="name,size"
        ).execute())
        orig_name = orig.get("name", "file")
        logger.info("Found original: %s (%s bytes)", orig_name, orig.get("size", "?"))

        copied = _exec_with_retry(lambda: service.files().copy(
            fileId=file_id, body={"name": orig_name}, fields="id,name",
        ).execute())
        copy_id = copied["id"]
        copy_name = copied.get("name", orig_name)
        logger.info("Copied to Drive (id=%s)", copy_id)

        dest_path.mkdir(parents=True, exist_ok=True)
        local_name = _sanitize_filename(copy_name)
        local_path = dest_path / local_name

        request = service.files().get_media(fileId=copy_id)
        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                status, done = _exec_with_retry(lambda: downloader.next_chunk())
                if status:
                    logger.debug("Download %d%%", int(status.progress() * 100))

        logger.info("Saved to %s", local_path)
        service.files().delete(fileId=copy_id).execute()
        logger.debug("Deleted copy from Drive")
        return str(local_path)

    except HttpError as e:
        status = e.resp.status
        reason = str(e)
        reason_lower = reason.lower()
        if status == 403 and "rateLimit" in reason_lower:
            logger.warning("API rate limit exceeded for file %s — try again later", file_id)
        elif status == 403 and "quota" in reason_lower:
            logger.warning("API quota exceeded for file %s", file_id)
        elif status == 404:
            logger.warning("File %s not found", file_id)
        elif status == 403:
            logger.warning("No access to file %s (may need 'Anyone with link' permission)", file_id)
        else:
            logger.warning("Drive API error %s: %s", status, reason)
    except Exception as e:
        logger.warning("Drive API unexpected error: %s", e)

    return None
