import string
import sys
import math
import requests
import time
import threading
from queue import Queue, Empty

CHUNK_SIZE = 10000
REQUEST_TIMEOUT = 10

CHARS = string.ascii_lowercase
N = 26


def total_space(max_length):
    return sum(N ** l for l in range(1, max_length + 1))


def make_chunks(total, chunk_size):
    chunks = []
    start = 0
    while start < total:
        end = min(total, start + chunk_size)
        chunks.append((start, end))
        start = end
    return chunks


def worker(hashed_password, max_length, chunk_queue, found_event, result, ports, lock, failures, max_fail=5):
    while not found_event.is_set():
        try:
            start, end = chunk_queue.get_nowait()
        except Empty:
            return

        # Select next port using Round-robin scheduling
        with lock:
            if not ports:
                print("All servers failed.")
                chunk_queue.task_done()
                return
            port = ports.pop(0)
            ports.append(port)

        url = f"http://127.0.0.1:{port}/crack_chunk"
        data = {
            "hashed_password": hashed_password,
            "max_length": max_length,
            "start_index": start,
            "end_index": end
        }
        try:
            resp = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                j = resp.json()
                if j.get("found"):
                    result['password'] = j.get('password')
                    found_event.set()
            else:
                raise Exception(f"Bad response, error {resp.status_code}")
        except Exception as e:
            with lock:
                failures[port] = failures.get(port, 0) + 1
                if failures[port] >= max_fail:
                    print(f"Removing port {port} due to {failures[port]} failures.")
                    try:    # safe guard
                        ports.remove(port)
                    except ValueError:
                        pass
            # Requeue the failed chunk so other worker can retry
            chunk_queue.put((start, end))
            time.sleep(0.5)
        finally:
            chunk_queue.task_done()


def main():
    if len(sys.argv) < 5:
        print("Usage: python client.py <start-port> <end-port> <md5_password> <max_password_length>")
        sys.exit(1)

    start_port = int(sys.argv[1])
    end_port = int(sys.argv[2])
    hashed_password = sys.argv[3]
    max_length = int(sys.argv[4])

    ports = list(range(start_port, end_port + 1))
    print(f"Using worker ports: {ports}")

    total = total_space(max_length)
    print(f"Total candidates (1..{max_length}): {total}")

    chunks = make_chunks(total, CHUNK_SIZE)
    print(f"Chunks: {len(chunks)} (chunk size {CHUNK_SIZE})")

    q = Queue()
    for c in chunks:
        q.put(c)

    found_event = threading.Event()
    result = {}
    lock = threading.Lock()
    failures = {}

    threads = []
    # One thread per port
    for port in ports:
        t = threading.Thread(
            target=worker,
            args=(hashed_password, max_length, q, found_event, result, ports, lock, failures)
            )
        t.daemon = True
        t.start()
        threads.append(t)

    start_time = time.time()
    # Wait for queue to be processed or someone password found
    try:
        while any(t.is_alive() for t in threads) and not found_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Interrupted.")
    end_time = time.time()
    duration = end_time - start_time

    if found_event.is_set():
        print("Password found:", result.get('password'))
        print("Time (s):", duration)
    else:
        print("Password not found (searched full space or services unavailable).")
        print("Time (s):", duration)


if __name__ == "__main__":
    main()
