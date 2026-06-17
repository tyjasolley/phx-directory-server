from flask import Flask, jsonify, request
from flask_cors import CORS
import csv, io, os, json, base64, urllib.request, urllib.error

app = Flask(__name__)
CORS(app)

# ── GitHub config (stores users.csv in your repo permanently) ──────────────
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = os.environ.get('GITHUB_REPO', '')   # e.g. "tyjasolley/phx-directory-server"
GITHUB_FILE  = 'users.csv'

COLS = ['Username','Full Name','Email','Department','Office',
        'Primary Card Number','Secondary Card Number','Created Date','Username alias']

def github_get():
    """Fetch users.csv from GitHub."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None, None
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    })
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            content = base64.b64decode(data['content']).decode('utf-8')
            sha = data['sha']
            return content, sha
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return '', None  # File doesn't exist yet
        raise

def github_put(content_str, sha=None):
    """Write users.csv to GitHub."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    payload = {
        'message': 'Update users.csv via PHX Directory',
        'content': base64.b64encode(content_str.encode('utf-8')).decode('utf-8'),
    }
    if sha:
        payload['sha'] = sha
    req = urllib.request.Request(url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        },
        method='PUT'
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status in (200, 201)
    except Exception as e:
        print('GitHub write error:', e)
        return False

def csv_to_users(content):
    if not content.strip():
        return []
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader if row.get('Username','').strip()]

def users_to_csv(users):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, extrasaction='ignore')
    w.writeheader()
    for u in users:
        w.writerow({c: u.get(c, '') for c in COLS})
    return buf.getvalue()

# ── Fallback: local file if GitHub not configured ─────────────────────────
def read_local():
    if not os.path.exists(GITHUB_FILE):
        return []
    with open(GITHUB_FILE, newline='', encoding='utf-8') as f:
        return [dict(row) for row in csv.DictReader(f) if row.get('Username','').strip()]

def write_local(users):
    with open(GITHUB_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        for u in users:
            w.writerow({c: u.get(c, '') for c in COLS})

# ── Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    users = get_users_data()
    return jsonify({'status': 'PHX Directory API running', 'users': len(users),
                    'storage': 'github' if GITHUB_TOKEN else 'local'})

def get_users_data():
    if GITHUB_TOKEN and GITHUB_REPO:
        content, _ = github_get()
        return csv_to_users(content or '')
    return read_local()

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify({'users': get_users_data()})

@app.route('/users', methods=['POST'])
def save_users():
    data = request.get_json()
    if not data or 'users' not in data:
        return jsonify({'error': 'Missing users array'}), 400
    users = [u for u in data['users'] if not u.get('Username','').startswith('__placeholder_')]
    csv_content = users_to_csv(users)

    if GITHUB_TOKEN and GITHUB_REPO:
        _, sha = github_get()
        ok = github_put(csv_content, sha)
        if not ok:
            return jsonify({'error': 'GitHub write failed'}), 500
    else:
        write_local(users)

    return jsonify({'success': True, 'count': len(users)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
