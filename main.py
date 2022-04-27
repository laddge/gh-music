import os
import time
import secrets
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Cookie, HTTPException
from fastapi.responses import RedirectResponse, Response, HTMLResponse, StreamingResponse
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


async def get_content(r):
    for chunk in r.iter_content(chunk_size=128):
        yield chunk


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
    if not b:
        r0 = requests.get(
            f"https://api.github.com/repos/{r}",
            headers={"Authorization": f"token {token}"}
        )
        if r0.status_code != 200:
            raise HTTPException(status_code=r0.status_code)
        b = r0.json()["default_branch"]
    if d:
        if d[-1] != "/":
            d += "/"
        if f:
            if f[-3:] not in ["mp3", "m4a", "wav", "ogg"]:
                raise HTTPException(status_code=400)
            r1 = requests.get(
                f"https://api.github.com/repos/{r}/contents{d}?ref={b}",
                headers={"Authorization": f"token {token}"}
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
                headers={"Authorization": f"token: {token}"},
                stream=True
            )
            if r2.status_code != 200:
                raise HTTPException(status_code=r2.status_code)
            return StreamingResponse(get_content(r2))
        r1 = requests.get(
            f"https://api.github.com/repos/{r}/contents{d}?ref={b}",
            headers={"Authorization": f"token {token}"}
        )
        if r1.status_code != 200:
            raise HTTPException(status_code=r1.status_code)
        files = []
        for obj in r1.json():
            if obj["type"] == "file":
                if obj["name"][-3:] in ["mp3", "m4a", "wav", "ogg"]:
                    files.append(obj["name"])
        return files
    r1 = requests.get(
        f"https://api.github.com/repos/{r}/git/trees/{b}?recursive=true",
        headers={"Authorization": f"token {token}"}
    )
    if r1.status_code != 200:
        raise HTTPException(status_code=r1.status_code)
    trees = ["/"]
    for tree in r1.json()["tree"]:
        if tree["type"] == "tree":
            trees.append("/" + tree["path"])
    return trees
