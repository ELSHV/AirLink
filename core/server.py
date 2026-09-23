import os
import sys
import zipfile
import threading
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse
from config import PORT, DOWNLOADS_DIR, signals

app = FastAPI()

def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

STAGING_DIR = os.path.join(DOWNLOADS_DIR, ".staging")
os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

PENDING_DOWNLOAD = {"filename": None, "path": None}

@app.get("/", response_class=HTMLResponse)
async def get_mobile_ui():
    template_path = get_resource_path(os.path.join("ui", "templates", "mobile.html"))
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/register-device")
async def register_device(request: Request):
    ua = request.headers.get("user-agent", "")
    device_name = "Мобильное устройство"
    if "iPhone" in ua:
        device_name = "Apple iPhone"
    elif "iPad" in ua:
        device_name = "Apple iPad"
    elif "Android" in ua:
        device_name = "Android устройство"
    elif "Windows" in ua:
        device_name = "ПК Windows"
    elif "Macintosh" in ua:
        device_name = "Apple Mac"

    signals.log_msg.emit(f"device_connected:{device_name}", "#d1d5db")
    return {"status": "registered"}

@app.post("/api/upload-batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    saved_count = 0
    for file in files:
        if not file.filename:
            continue
        save_path = os.path.join(DOWNLOADS_DIR, file.filename)
        base, ext = os.path.splitext(file.filename)
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(DOWNLOADS_DIR, f"{base}_{counter}{ext}")
            counter += 1

        with open(save_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
        saved_count += 1

    signals.files_received.emit(saved_count)
    return {"status": "ok", "count": saved_count}

@app.post("/api/prepare-pc-files")
async def prepare_pc_files(files: List[UploadFile] = File(...)):
    if len(files) == 1:
        f = files[0]
        out_path = os.path.join(STAGING_DIR, f.filename)
        with open(out_path, "wb") as buf:
            while chunk := await f.read(1024 * 1024):
                buf.write(chunk)
        PENDING_DOWNLOAD["filename"] = f.filename
        PENDING_DOWNLOAD["path"] = out_path
    else:
        zip_path = os.path.join(STAGING_DIR, "AirLink_Files.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                f_path = os.path.join(STAGING_DIR, f.filename)
                with open(f_path, "wb") as buf:
                    while chunk := await f.read(1024 * 1024):
                        buf.write(chunk)
                zipf.write(f_path, arcname=f.filename)
        PENDING_DOWNLOAD["filename"] = "AirLink_Files.zip"
        PENDING_DOWNLOAD["path"] = zip_path

    return {"status": "ready"}

@app.get("/api/check-incoming")
async def check_incoming():
    if PENDING_DOWNLOAD["path"] and os.path.exists(PENDING_DOWNLOAD["path"]):
        return {"ready": True, "filename": PENDING_DOWNLOAD["filename"]}
    return {"ready": False}

@app.get("/api/download-incoming")
async def download_incoming():
    path = PENDING_DOWNLOAD["path"]
    if path and os.path.exists(path):
        name = PENDING_DOWNLOAD["filename"]
        PENDING_DOWNLOAD["path"] = None
        PENDING_DOWNLOAD["filename"] = None
        return FileResponse(path, filename=name)
    return {"error": "not found"}

def run_uvicorn():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_config=None, access_log=False)

def start_server():
    server_thread = threading.Thread(target=run_uvicorn, daemon=True)
    server_thread.start()