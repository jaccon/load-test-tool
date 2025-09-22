# Stress Test Script

Quick guide for `_stressTest.py`.

Requirements:

```sh
pip install requests tqdm
```

Run examples:

```sh
# default values (editable in file or via env)
python3 _stressTest.py

# override via CLI
python3 _stressTest.py --url https://example.com --requests 500 --concurrency 50

# or use environment variables (CLI flags override env):
export STRESS_TOTAL_REQUESTS=1000
export STRESS_CONCURRENCY=100
export STRESS_TARGET_URL=https://example.com
python3 _stressTest.py
```

Notes:
- The script uses multiple threads and a `requests.Session` per worker for connection pooling.
- Use responsibly and only test endpoints you own or have permission to test.
- For very large request counts, monitor your local system resources.
