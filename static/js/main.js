function login() {
    const clientId = document.getElementById('clientId').value;
    const redirect = encodeURIComponent(location.href);
    const redirectURI = encodeURIComponent('https://gh-music.laddge.net/callback?redirect=' + redirect);
    location.href = 'https://github.com/login/oauth/authorize?client_id=' + clientId + '&scope=repo&redirect_uri=' + redirectURI;
}

function getParam(key) {
    const params = location.search.slice(1).split('&');
    let value = ''
    params.forEach(paramStr => {
        if (paramStr.slice(0, key.length + 1) == key + '=') {
            value = paramStr.slice(key.length + 1);
        }
    });
    return value;
}

function formatSec(sec) {
    let m = Math.floor(sec / 60);
    if (m >= 10) {
        m = String(m);
    } else {
        m = '0' + String(m);
    }
    const s = ('0' + String(Math.floor(sec % 60))).slice(-2);
    return m + ':' + s;
}

function list() {
    const repo = getParam('r');
    const branch = getParam('b');
    const dir = getParam('d');
    if (!repo || !branch || !dir) {
        console.log('aho');
        return;
    }
    const listEl = document.getElementById('list');
    const loading = document.getElementById('loading');
    listEl.classList.add('d-none');
    loading.classList.remove('d-none');
    const api = '/api?r=' + repo + '&b=' + branch + '&d=' + dir;
    fetch(api)
        .then(res => {
            if (res.ok) {
                return res.json();
            } else {
                throw new Error(res.status);
            }
        })
        .then(data => {
            loading.classList.add('d-none');
            listEl.classList.remove('d-none');
            const listBody = document.getElementById('listBody');
            data.forEach(row => {
                let rowHTML = '<tr>';
                if (row.title) {
                    rowHTML += '<td>' + row.title + '</td>';
                } else {
                    rowHTML += '<td>' + row.name + '</td>';
                }
                if (row.artist) {
                    rowHTML += '<td>' + row.artist + '</td>';
                } else {
                    rowHTML += '<td>Null</td>';
                }
                rowHTML += '<td>' + formatSec(row.length) + '</td><input type="hidden" value="' + row.apic + '"></tr>';
                listBody.innerHTML += rowHTML;
            });
        })
        .catch(err => {
            loading.classList.add('d-none');
            document.getElementById('error').innerText = 'Something wrong.';
            console.log(err);
        });
}

list();
