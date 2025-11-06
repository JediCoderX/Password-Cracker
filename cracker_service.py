# cracker_service.py
from flask import Flask, request, jsonify
import itertools
import string
import hashlib

app = Flask(__name__)

CHARS = string.ascii_lowercase
N = len(CHARS)

def index_to_password(idx, max_length):
    # Map a global index to the password string.
    if idx < 0:
        return None
    rem = idx
    for length in range(1, max_length + 1):
        block_size = N ** length
        # Convert remaining
        if rem < block_size:
            offset = rem
            digits = []
            for pow_i in range(length - 1, -1, -1):
                place = N ** pow_i
                digit = offset // place
                offset = offset % place
                digits.append(digit)
            return ''.join(CHARS[d] for d in digits)
        rem -= block_size
    # Out of range
    return None

def brutefoce_password(hashed_password, max_length, start_index, end_index):
    for idx in range(start_index, end_index):
        pwd = index_to_password(idx, max_length)
        if pwd is None:
            break
        if hashlib.md5(pwd.encode()).hexdigest() == hashed_password:
            return pwd
    return None

@app.route('/crack_chunk', methods=['POST'])
def crack_chunk():
    data = request.get_json()
    required = ('hashed_password', 'max_length', 'start_index', 'end_index')
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    hashed = data['hashed_password']
    max_length = int(data['max_length'])
    start_index = int(data['start_index'])
    end_index = int(data['end_index'])

    if start_index >= end_index:
        return jsonify({"error": "start_index must be < end_index"}), 400

    found = brutefoce_password(hashed, max_length, start_index, end_index)
    if found:
        return jsonify({"found": True, "password": found})
    else:
        return jsonify({"found": False}), 200

# Part 1
# @app.route('/crack', methods=['POST'])
# def crack_full():
#     data = request.get_json()
#     if not data or 'hashed_password' not in data or 'max_length' not in data:
#         return jsonify({"error": "Missing fields"}), 400
#     hashed = data['hashed_password']
#     max_length = int(data['max_length'])
#     # full brute force (not recommended for large spaces)
#     total = sum(N ** l for l in range(1, max_length + 1))
#     found = brutefoce_password(hashed, max_length, 0, total)
#     if found:
#         return jsonify({"password": found})
#     else:
#         return jsonify({"password": None, "message": "Not found"}), 404