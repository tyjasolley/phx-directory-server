from flask import Flask, jsonify, request
from flask_cors import CORS
import csv, io, os

app = Flask(__name__)
CORS(app)  # Allow all origins

DATA_FILE = 'users.csv'
COLS = ['Username','Full Name','Email','Department','Office',
        'Primary Card Number','Secondary Card Number','Created Date','Username alias']

def read_users():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader if row.get('Username','').strip()]

def write_users(users):
    with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        writer.writeheader()
        for u in users:
            writer.writerow({c: u.get(c, '') for c in COLS})

@app.route('/')
def index():
    return jsonify({'status': 'PHX Directory API running', 'users': len(read_users())})

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify({'users': read_users()})

@app.route('/users', methods=['POST'])
def save_users():
    data = request.get_json()
    if not data or 'users' not in data:
        return jsonify({'error': 'Missing users array'}), 400
    users = [u for u in data['users'] if not u.get('Username','').startswith('__placeholder_')]
    write_users(users)
    return jsonify({'success': True, 'count': len(users)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
