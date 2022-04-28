import os
import time
import secrets
import base64
from io import BytesIO
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Cookie, HTTPException
from fastapi.responses import RedirectResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import requests
import cryptocode
from mutagen.id3 import ID3
import mutagen

GH_CLIENT_ID = os.getenv("GH_CLIENT_ID")
GH_CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def middleware(request: Request, call_next):
    if "herokuapp" in urlparse(str(request.url)).netloc:
        domain = os.getenv("DOMAIN")
        if domain:
            url = urlparse(str(request.url))._replace(netloc=domain).geturl()
            response = RedirectResponse(url)
        else:
            response = await call_next(request)
    else:
        if request.method == "HEAD":
            if urlparse(str(request.url)).path == "/":
                response = Response()
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
    return response


def encrypt_token(token):
    timestamp = os.getenv("KEY_UPDATED")
    timestamp = int(timestamp) if timestamp else 0
    if timestamp > time.time() - 2600000:
        if os.getenv("KEY_STR"):
            keystr = os.getenv("KEY_STR")
        else:
            keystr = secrets.token_hex()
            os.environ["KEY_STR"] = keystr
            os.environ["KEY_UPDATED"] = str(int(time.time()))
    else:
        keystr = secrets.token_hex()
        os.environ["KEY_STR"] = keystr
        os.environ["KEY_UPDATED"] = str(int(time.time()))
    return cryptocode.encrypt(token, keystr)


def decrypt_token(encrypted_token):
    timestamp = os.getenv("KEY_UPDATED")
    timestamp = int(timestamp) if timestamp else 0
    if timestamp > time.time() - 2600000:
        keystr = os.getenv("KEY_STR")
        return cryptocode.decrypt(encrypted_token, keystr)
    else:
        return


@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request, encrypted_token: Optional[str] = Cookie(None)):
    login = ""
    if encrypted_token:
        token = decrypt_token(encrypted_token)
        if token:
            headers = {"Authorization": f"token {token}"}
            r = requests.get("https://api.github.com/user", headers=headers)
            if r.status_code == 200:
                login = r.json()["login"]
    data = {
        "request": request,
        "login": login,
        "client_id": GH_CLIENT_ID
    }
    return templates.TemplateResponse("page.html", data)


@app.get("/callback")
async def get_callback(code: str):
    url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    params = {
        "client_id": GH_CLIENT_ID,
        "client_secret": GH_CLIENT_SECRET,
        "code": code
    }
    r = requests.get(url, headers=headers, params=params)
    encrypted_token = encrypt_token(r.json()["access_token"])
    response = RedirectResponse("/")
    response.set_cookie(key="encrypted_token", value=encrypted_token)
    return response


@app.get("/logout")
async def get_logout():
    response = RedirectResponse("/")
    response.set_cookie(key="encrypted_token", value="")
    return response


@app.get("/api")
async def get_api(
        r: Optional[str] = None,
        b: Optional[str] = None,
        d: Optional[str] = None,
        f: Optional[str] = None,
        encrypted_token: Optional[str] = Cookie(None)):
    if not r:
        raise HTTPException(status_code=400)
    token = decrypt_token(encrypted_token) if encrypted_token else None
    headers = {"Authorization": f"token {token}"} if token else None
    if d:
        if not b:
            r0 = requests.get(
                f"https://api.github.com/repos/{r}",
                headers=headers
            )
            if r0.status_code != 200:
                raise HTTPException(status_code=r0.status_code)
            b = r0.json()["default_branch"]
        if d[-1] != "/":
            d += "/"
        if f:
            if f[-3:] not in ["mp3", "m4a", "wav", "ogg"]:
                raise HTTPException(status_code=400)
            r1 = requests.get(
                f"https://api.github.com/repos/{r}/contents{d}?ref={b}",
                headers=headers
            )
            if r1.status_code != 200:
                raise HTTPException(status_code=r1.status_code)
            dl_url = ""
            for obj in r1.json():
                if obj["name"] == f:
                    dl_url = obj["download_url"]
            if not dl_url:
                raise HTTPException(status_code=404)
            r2 = requests.get(
                dl_url,
                headers=headers,
                stream=True
            )
            if r2.status_code != 200:
                raise HTTPException(status_code=r2.status_code)
            return Response(content=r2.content, media_type=r2.headers["Content-Type"])
        r1 = requests.get(
            f"https://api.github.com/repos/{r}/contents{d}?ref={b}",
            headers=headers
        )
        if r1.status_code != 200:
            raise HTTPException(status_code=r1.status_code)
        files = []
        for obj in r1.json():
            if obj["type"] != "file":
                continue
            if obj["name"][-3:] not in ["mp3", "m4a", "wav", "ogg"]:
                continue
            audio = {"name": obj["name"]}
            r2 = requests.get(
                obj["download_url"],
                headers=headers,
                stream=True
            )
            if r2.status_code != 200:
                raise HTTPException(status_code=r2.status_code)
            try:
                tags = ID3(BytesIO(r2.content))
                audio["title"] = tags.get("TIT2").text[0] if tags.get("TIT2") else ""
                audio["artist"] = tags.get("TPE1").text[0] if tags.get("TPE1") else ""
                apic = tags.get("APIC:")
                audio["apic"] = base64.b64encode(apic.data).decode() if apic else ""
                audio_file = mutagen.File(BytesIO(r2.content))
                audio["length"] = audio_file.info.length
                files.append(audio)
            except Exception:
                pass
        return files
    if not b:
        r0 = requests.get(
            f"https://api.github.com/repos/{r}",
            headers=headers
        )
        if r0.status_code != 200:
            raise HTTPException(status_code=r0.status_code)
        r1 = requests.get(
            f"https://api.github.com/repos/{r}/branches",
            headers=headers
        )
        if r1.status_code != 200:
            raise HTTPException(status_code=r1.status_code)
        res = {
            "branches": [br["name"] for br in r1.json()],
            "default_branch": r0.json()["default_branch"]
        }
        return res
    r0 = requests.get(
        f"https://api.github.com/repos/{r}/git/trees/{b}?recursive=true",
        headers=headers
    )
    if r0.status_code != 200:
        raise HTTPException(status_code=r0.status_code)
    trees = ["/"]
    for tree in r0.json()["tree"]:
        if tree["type"] == "tree":
            trees.append("/" + tree["path"])
    return trees
