import json
import os
import threading

import gspread
from google.oauth2.service_account import Credentials

from finance_bot.settings import (
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_CREDENTIALS_JSON,
    SPREADSHEET_NAME,
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_SHEET = None
_SHEET_LOCK = threading.Lock()


def conectar_planilha():
    global _SHEET

    if _SHEET is not None:
        return _SHEET

    with _SHEET_LOCK:
        if _SHEET is not None:
            return _SHEET

        if GOOGLE_CREDENTIALS_JSON:
            creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(
                creds_info, scopes=SCOPES
            )
        elif (
            GOOGLE_CREDENTIALS_FILE
            and os.path.exists(GOOGLE_CREDENTIALS_FILE)
        ):
            credentials = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
            )
        else:
            raise ValueError("Credenciais do Google Sheets não encontradas.")

        client = gspread.authorize(credentials)
        _SHEET = client.open(SPREADSHEET_NAME).sheet1
        return _SHEET
