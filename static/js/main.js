function login() {
    const clientId = document.getElementById('clientId').value;
    const redirect = encodeURIComponent(location.href);
    const redirectURI = encodeURIComponent('https://gh-music.laddge.net/callback?redirect=' + redirect);
    location.href = 'https://github.com/login/oauth/authorize?client_id=' + clientId + '&scope=repo&redirect_uri=' + redirectURI;
}

function resetOpener() {
    const inputRepo = document.getElementById('inputRepo');
    const chackRepoSpinner = document.getElementById('checkRepoSpinner');
    const chackRepoText = document.getElementById('checkRepoText');
    const inputBranch = document.getElementById('inputBranch');
    const listDirSpinner = document.getElementById('listDirSpinner');
    const listDirPlaceholder = document.getElementById('listDirPlaceholder');
    const listDirForm = document.getElementById('listDirForm');
    const openBtn = document.getElementById('openBtn');
    inputRepo.classList.remove('is-valid');
    inputRepo.classList.remove('is-invalid');
    checkRepoSpinner.classList.add('d-none');
    checkRepoText.classList.remove('d-none');
    inputBranch.innerHTML = '<option selected>-----</option>';
    listDirSpinner.classList.add('d-none');
    listDirPlaceholder.classList.remove('d-none');
    listDirForm.innerHTML = '';
    openBtn.disabled = true;
}

function listDir() {
    const spinner = document.getElementById('listDirSpinner');
    const placeholder = document.getElementById('listDirPlaceholder');
    const form = document.getElementById('listDirForm');
    const inputRepo = document.getElementById('inputRepo');
    const inputBranch = document.getElementById('inputBranch');
    const openBtn = document.getElementById('openBtn');
    openBtn.disabled = true;
    placeholder.classList.add('d-none');
    form.innerHTML = '';
    spinner.classList.remove('d-none');
    const api = '/api?r=' + inputRepo.value + '&b=' + inputBranch.value;
    fetch(api)
        .then(res => {
            if (res.ok) {
                return res.json();
            } else {
                throw new Error(res.status);
            }
        })
        .then(data => {
            let html = '<div class="form-check ps-0 my-0"><label class="form-check-label"><input type="radio" class="form-check-input d-none" name="listDir" value="/" checked><span class="rounded-1 px-1">/</span></label></div>';
            if (data.length > 1) {
                const lines = data.slice(1);
                let dnn = [];
                lines.forEach(line => {
                    const depth = line.split('/').length - 1;
                    const name = line.split('/')[depth];
                    dnn.push([depth, name]);
                });
                let vrs = [];
                for (let i = 0; i < dnn.length; i++) {
                    let _vrs = [];
                    vrs.forEach(vr => {
                        if (vr < dnn[i][0]) {
                            _vrs.push(vr);
                        }
                    });
                    vrs = _vrs;
                    for (let j = i + 1; j < dnn.length; j++) {
                        if (dnn[j][0] < dnn[i][0]) {
                            break;
                        }
                        if (dnn[j][0] == dnn[i][0]) {
                            vrs.push(dnn[i][0]);
                            break;
                        }
                    }
                    let indent = '';
                    for (let d = 0; d < dnn[i][0] - 1; d++) {
                        if (vrs.indexOf(d + 1) != -1) {
                            indent += '│&nbsp;&nbsp;&nbsp;';
                        } else {
                            indent += '&nbsp;&nbsp;&nbsp;&nbsp;';
                        }
                    }
                    let end = '└──&nbsp;';
                    if (vrs.indexOf(dnn[i][0]) != -1) {
                        end = '├──&nbsp;';
                    }
                    const value = lines[i];
                    html += '<div class="form-check ps-0 my-0"><label class="form-check-label"><input type="radio" class="form-check-input d-none" name="listDir" value="' + value + '">' + indent + end + '<span class="rounded-1 px-1">' + dnn[i][1] + '</span></label></div>';
                }
            }
            form.innerHTML = html;
            spinner.classList.add('d-none');
            openBtn.disabled = false;
        })
        .catch(err => {
            spinner.classList.add('d-none');
            console.log(err);
        });
}

function checkRepo() {
    const spinner = document.getElementById('checkRepoSpinner');
    const text = document.getElementById('checkRepoText');
    const inputRepo = document.getElementById('inputRepo');
    const inputBranch = document.getElementById('inputBranch');
    inputRepo.classList.remove('is-valid');
    inputRepo.classList.remove('is-invalid');
    text.classList.add('d-none');
    spinner.classList.remove('d-none');
    const api = '/api?r=' + inputRepo.value;
    fetch(api)
        .then(res => {
            if (res.ok) {
                return res.json();
            } else {
                throw new Error(res.status);
            }
        })
        .then(data => {
            inputBranch.innerHTML = '<option selected>' + data.default_branch + '</option>';
            data.branches.forEach(branch => {
                if (branch != data.default_branch) {
                    inputBranch.innerHTML += '<option>' + branch + '</option>';
                }
            });
            spinner.classList.add('d-none');
            text.classList.remove('d-none');
            inputRepo.classList.add('is-valid');
            listDir();
        })
        .catch(err => {
            spinner.classList.add('d-none');
            text.classList.remove('d-none');
            inputRepo.classList.add('is-invalid');
            console.log(err);
        });
}

function openDir() {
    const repo = document.getElementById('inputRepo').value;
    const branch = document.getElementById('inputBranch').value;
    const dir = document.getElementById('listDirForm').elements['listDir'].value;
    location.href = '/?r=' + repo + '&b=' + branch + '&d=' + dir;
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
