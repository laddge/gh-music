import os
import time
import secrets
import json
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Cookie
from fastapi.responses import RedirectResponse, Response, HTMLResponse
from typing import Optional
import requests
import cryptocode

GH_CLIENT_ID = os.getenv("GH_CLIENT_ID")
GH_CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET")

app = FastAPI()


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
            os.environ["KEY_UPDATED"] = str(time.time())
    else:
        keystr = secrets.token_hex()
        os.environ["KEY_STR"] = keystr
        os.environ["KEY_UPDATED"] = str(time.time())
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
async def get_root(encrypted_token: Optional[str] = Cookie(None)):
    if encrypted_token:
        token = decrypt_token(encrypted_token)
        if token:
            headers = {"Authorization": f"token {token}"}
            r = requests.get("https://api.github.com/user", headers=headers)
            if r.status_code == 200:
                return "Logined as {}(@{}).".format(r.json()["name"], r.json()["login"])
    url = f"https://github.com/login/oauth/authorize?client_id={GH_CLIENT_ID}&scope=repo"
    return f"<a href='{url}'>Login with GitHub</a>"


@app.get("/callback")
async def get_callback(code: str):
    url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = json.dumps({
        "client_id": GH_CLIENT_ID,
        "client_secret": GH_CLIENT_SECRET,
        "code": code
    })
    r = requests.post(url, headers=headers, data=data)
    encrypted_token = encrypt_token(r.json()["access_token"])
    response = RedirectResponse("/")
    response.set_cookie(key="encrypted_token", value=encrypted_token)
    return response
