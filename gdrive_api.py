import json
import logging
import os
import pickle
import random
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

import config
from config import CREDENTIALS_FILE, TOKEN_FILE, DATA_DIR

logger = logging.getLogger("gdrive_api")

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_credentials_path() -> Path:
    target = Path(config.DATA_DIR) / "credentials.json"
    if target.exists():
        return target
    if Path(config.CREDENTIALS_FILE).exists():
        return Path(config.CREDENTIALS_FILE)
    return target


def _get_token_path() -> Path:
    target = Path(config.DATA_DIR) / "token.pickle"
    if target.exists():
        return target
    if Path(config.TOKEN_FILE).exists():
        return Path(config.TOKEN_FILE)
    return target


def check_gdrive_status() -> Dict[str, Any]:
    """Returns a dictionary detailing the GDrive API setup and token health."""
    creds_p = _get_credentials_path()
    token_p = _get_token_path()

    has_creds = creds_p.exists()
    has_token = token_p.exists()
    token_valid = False
    details = ""
    client_id = ""
    project_id = ""
    user_email = ""
    user_name = ""

    if has_creds:
        try:
            raw = json.loads(creds_p.read_text(encoding="utf-8"))
            info = raw.get("installed") or raw.get("web") or {}
            client_id = info.get("client_id", "")
            project_id = info.get("project_id", "")
        except Exception:
            pass

    try:
        from desktop.backend.settings_manager import settings_manager
        user_info = settings_manager.get_gdrive_user_info()
        user_email = user_info.get("email", "")
        user_name = user_info.get("name", "")
    except Exception:
        pass

    if not has_creds:
        details = "Missing credentials.json file. Import it in Settings."
    elif not has_token:
        details = "Credentials present, but not authenticated yet. Click 'Sign In with Google'."
    else:
        try:
            with open(token_p, "rb") as f:
                creds = pickle.load(f)
            if creds and creds.valid:
                token_valid = True
                details = f"Authenticated & ready{f' as {user_email}' if user_email else ''}"
            elif creds and creds.expired and creds.refresh_token:
                token_valid = True
                details = f"Token valid (auto-refreshes on request){f' as {user_email}' if user_email else ''}"
            else:
                details = "Token invalid or expired without refresh token"
        except Exception as e:
            details = f"Failed to read token: {e}"

    return {
        "credentials_present": has_creds,
        "token_present": has_token,
        "authenticated": token_valid,
        "details": details,
        "credentials_path": str(creds_p),
        "token_path": str(token_p),
        "client_id": client_id,
        "project_id": project_id,
        "user_email": user_email,
        "user_name": user_name,
    }


def import_credentials_content(content: str) -> Dict[str, Any]:
    """Validates and saves credentials.json content."""
    try:
        parsed = json.loads(content.strip())
    except Exception as e:
        return {"success": False, "message": f"Invalid JSON format: {e}"}

    client_info = parsed.get("installed") or parsed.get("web")
    if not client_info or not isinstance(client_info, dict):
        return {
            "success": False,
            "message": "Unrecognized format: credentials.json must contain an 'installed' or 'web' OAuth client config.",
        }

    client_id = client_info.get("client_id")
    client_secret = client_info.get("client_secret")
    if not client_id or not client_secret:
        return {
            "success": False,
            "message": "Missing 'client_id' or 'client_secret' in the provided credentials.",
        }

    target_file = Path(config.DATA_DIR) / "credentials.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update config module pointers
    config.CREDENTIALS_FILE = target_file

    # Remove stale token since credentials changed
    token_p = _get_token_path()
    if token_p.exists():
        try:
            token_p.unlink()
        except Exception:
            pass

    try:
        from desktop.backend.settings_manager import settings_manager
        settings_manager.set_gdrive_user_info("", "")
    except Exception:
        pass

    logger.info("Imported credentials.json successfully (client_id: %s...)", client_id[:16])
    return {
        "success": True,
        "message": f"Credentials imported successfully (Project: {client_info.get('project_id', 'OAuth Client')})",
        "client_id": client_id,
        "project_id": client_info.get("project_id", ""),
        "path": str(target_file),
    }


def import_credentials_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Imports credentials.json from a local file path."""
    p = Path(file_path)
    if not p.exists():
        return {"success": False, "message": f"File does not exist: {file_path}"}
    try:
        content = p.read_text(encoding="utf-8")
        return import_credentials_content(content)
    except Exception as e:
        return {"success": False, "message": f"Failed to read file: {e}"}


def _get_service():
    creds_p = _get_credentials_path()
    token_p = _get_token_path()

    if not creds_p.exists():
        logger.warning("credentials.json not found (%s) — Drive API unavailable", creds_p)
        return None

    creds = None
    if token_p.exists():
        try:
            with open(token_p, "rb") as f:
                creds = pickle.load(f)
        except Exception as e:
            logger.warning("Failed loading token file %s: %s", token_p, e)
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.warning("Failed refreshing token: %s", e)
            creds = None

    if not creds or not creds.valid:
        logger.warning("Google Drive token not present or invalid. Authentication required.")
        return None

    return build("drive", "v3", credentials=creds)


def authenticate_interactive() -> Dict[str, Any]:
    """
    Runs OAuth flow, opens browser, acquires token, saves token.pickle,
    and returns user information. Should be executed in a background thread.
    """
    creds_p = _get_credentials_path()
    token_p = Path(config.DATA_DIR) / "token.pickle"

    if not creds_p.exists():
        return {"success": False, "message": "credentials.json is missing. Please import it first."}

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_p), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    except Exception as e:
        logger.error("OAuth authorization failed: %s", e)
        return {"success": False, "message": f"Authorization error: {e}"}

    try:
        token_p.parent.mkdir(parents=True, exist_ok=True)
        with open(token_p, "wb") as f:
            pickle.dump(creds, f)
        config.TOKEN_FILE = token_p
    except Exception as e:
        logger.warning("Failed saving token to %s: %s", token_p, e)

    email = ""
    name = ""
    try:
        service = build("drive", "v3", credentials=creds)
        about = service.about().get(fields="user(displayName,emailAddress)").execute()
        user = about.get("user", {})
        email = user.get("emailAddress", "")
        name = user.get("displayName", "")
        from desktop.backend.settings_manager import settings_manager
        settings_manager.set_gdrive_user_info(email, name)
    except Exception as e:
        logger.warning("Failed to fetch user info after auth: %s", e)

    msg = f"Successfully authenticated as {name} ({email})" if name else (
        f"Successfully authenticated as {email}" if email else "Successfully authenticated with Google Drive!"
    )
    return {"success": True, "message": msg, "email": email, "name": name}


def test_connection() -> Dict[str, Any]:
    """Tests Google Drive API access and queries user details."""
    creds_p = _get_credentials_path()
    token_p = _get_token_path()

    if not creds_p.exists():
        return {"success": False, "message": "credentials.json missing. Please import it first."}
    if not token_p.exists():
        return {"success": False, "message": "Not authenticated. Click 'Sign In with Google' to authenticate."}

    service = _get_service()
    if service is None:
        return {"success": False, "message": "Unable to initialize Google Drive service. Please re-authenticate."}

    try:
        about = service.about().get(fields="user(displayName,emailAddress),storageQuota").execute()
        user = about.get("user", {})
        email = user.get("emailAddress", "Unknown")
        name = user.get("displayName", "")

        from desktop.backend.settings_manager import settings_manager
        settings_manager.set_gdrive_user_info(email, name)

        msg = f"✓ Connected to Google Drive as {name} ({email})" if name else f"✓ Connected to Google Drive as {email}"
        return {"success": True, "message": msg, "email": email, "name": name}
    except Exception as e:
        return {"success": False, "message": f"Google Drive API test failed: {e}"}


def disconnect_gdrive(delete_credentials: bool = False) -> Dict[str, Any]:
    """Clears token and optionally removes credentials.json."""
    token_p = _get_token_path()
    if token_p.exists():
        try:
            token_p.unlink()
        except Exception:
            pass

    if delete_credentials:
        creds_p = _get_credentials_path()
        if creds_p.exists():
            try:
                creds_p.unlink()
            except Exception:
                pass

    try:
        from desktop.backend.settings_manager import settings_manager
        settings_manager.set_gdrive_user_info("", "")
    except Exception:
        pass

    return {"success": True, "message": "Google Drive disconnected"}


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


def copy_and_download(
    file_id: str,
    dest_path: Union[str, Path],
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_event: Optional[Any] = None,
) -> Optional[str]:
    """
    Downloads a Google Drive file by creating a temporary copy in the user's
    Drive to bypass public quota exhaustion ('Too many users downloaded recently').
    """
    def _log(msg: str):
        if log_cb:
            try:
                log_cb(msg)
            except Exception:
                pass
        logger.info(msg)

    service = _get_service()
    if service is None:
        _log("Google Drive API service unavailable (not authenticated or credentials missing)")
        return None

    try:
        _log(f"Querying Google Drive file ID: {file_id}...")
        orig = _exec_with_retry(lambda: service.files().get(
            fileId=file_id, fields="name,size"
        ).execute())
        orig_name = orig.get("name", "file")
        total_size = int(orig.get("size", 0) or 0)
        _log(f"Found original model file: '{orig_name}' ({round(total_size / (1024*1024), 1)} MB)")

        _log(f"Bypassing quota limit: Creating temporary copy of '{orig_name}' in your Google Drive...")
        copied = _exec_with_retry(lambda: service.files().copy(
            fileId=file_id, body={"name": orig_name}, fields="id,name",
        ).execute())
        copy_id = copied["id"]
        copy_name = copied.get("name", orig_name)

        dest_path = Path(dest_path)
        dest_path.mkdir(parents=True, exist_ok=True)
        local_name = _sanitize_filename(copy_name)
        local_path = dest_path / local_name

        _log(f"Downloading model archive from private Drive copy...")
        request = service.files().get_media(fileId=copy_id)
        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=4 * 1024 * 1024)
            done = False
            while not done:
                if cancel_event is not None and cancel_event.is_set():
                    _log("Download cancelled by user.")
                    break
                status, done = _exec_with_retry(lambda: downloader.next_chunk())
                if status and progress_cb:
                    downloaded = int(total_size * status.progress()) if total_size else 0
                    progress_cb(downloaded, total_size, local_name)

        if cancel_event is not None and cancel_event.is_set():
            if local_path.exists():
                local_path.unlink()
            try:
                service.files().delete(fileId=copy_id).execute()
            except Exception:
                pass
            return None

        # Clean up temporary copy in user's Drive
        try:
            service.files().delete(fileId=copy_id).execute()
            logger.debug("Deleted temporary copy %s from Drive", copy_id)
        except Exception as e:
            logger.warning("Could not delete temporary copy %s: %s", copy_id, e)

        _log(f"✓ Model successfully downloaded via Google Drive API: {local_name}")
        return str(local_path)

    except HttpError as e:
        status = e.resp.status
        reason = str(e)
        reason_lower = reason.lower()
        if status == 403 and "rateLimit" in reason_lower:
            _log("API rate limit exceeded — please try again in a few minutes.")
        elif status == 403 and "quota" in reason_lower:
            _log("Google Drive personal quota exceeded.")
        elif status == 404:
            _log(f"File ID {file_id} not found on Google Drive.")
        elif status == 403:
            _log(f"Access denied to file ID {file_id} (may require 'Anyone with link' permission).")
        else:
            _log(f"Google Drive API error ({status}): {reason}")
    except Exception as e:
        _log(f"Unexpected error during Google Drive API download: {e}")

    return None
