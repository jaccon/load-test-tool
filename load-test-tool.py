#!/usr/bin/env python3
"""
Multithreaded HTTP stress test script.

Usage:
  - Edit the top-level `TOTAL_REQUESTS` variable to set the number of requests,
    or set the environment variable `STRESS_TOTAL_REQUESTS`.
  - You can also override using CLI flags: `--requests`, `--concurrency`, `--url`.

Install requirements:
    pip install requests tqdm

Example:
    python _stressTest.py --url https://example.com --requests 200 --concurrency 20

The script uses a `tqdm` progress bar to show progress across threads and prints
a short summary with success/failure counts and latency statistics.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from requests import RequestException
from tqdm import tqdm

# External (editable) defaults
TOTAL_REQUESTS = int(os.environ.get("STRESS_TOTAL_REQUESTS", "100"))
DEFAULT_CONCURRENCY = int(os.environ.get("STRESS_CONCURRENCY", "10"))
DEFAULT_URL = os.environ.get("STRESS_TARGET_URL", "https://example.com")


def make_request(session: requests.Session, method: str, url: str, timeout: float = 10.0, data: Optional[bytes] = None, headers: Optional[dict] = None):
    """Send a single HTTP request using the provided Session.

    Returns a tuple: (success: bool, status_code: Optional[int], elapsed_seconds: float, error_message: Optional[str])
    """
    start = time.perf_counter()
    try:
        resp = session.request(method=method, url=url, timeout=timeout, data=data, headers=headers)
        elapsed = time.perf_counter() - start
        return True, resp.status_code, elapsed, None
    except RequestException as e:
        elapsed = time.perf_counter() - start
        return False, None, elapsed, str(e)


def run_stress_test(url: str, total_requests: int, concurrency: int, method: str = "GET", timeout: float = 10.0, data: Optional[bytes] = None, headers: Optional[dict] = None, save_report: bool = False):
    """Run the stress test and print a summary.

    Returns a dict with metrics.
    """
    metrics_lock = threading.Lock()
    success_count = 0
    failure_count = 0
    latencies = []
    statuses = Counter()

    # Prepare a requests.Session per worker thread for connection pooling.
    sessions = [requests.Session() for _ in range(concurrency)]
    stop_requested = threading.Event()

    # Platform-specific single-key listener to set stop_requested when 's' or 'S' pressed.
    def key_listener():
        try:
            import select
            if os.name == 'nt':
                import msvcrt
                while not stop_requested.is_set():
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch.lower() == 's':
                            stop_requested.set()
                            break
                    time.sleep(0.1)
            else:
                import tty, termios
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    while not stop_requested.is_set():
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            ch = sys.stdin.read(1)
                            if ch.lower() == 's':
                                stop_requested.set()
                                break
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            # If key listening fails, just ignore and rely on Ctrl+C
            return

    # start background listener
    listener_thread = threading.Thread(target=key_listener, daemon=True)
    listener_thread.start()

    def task(i: int):
        # Round-robin pick a session to reduce contention
        session = sessions[i % len(sessions)]
        return make_request(session, method, url, timeout=timeout, data=data, headers=headers)

    futures = []
    pbar = tqdm(total=total_requests if total_requests < 10**9 else None, desc="Requests", unit="req")

    test_start = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as exe:
            submitted = 0
            # submit tasks in batches and stop if requested
            batch_size = max(1, concurrency * 5)
            while submitted < total_requests and not stop_requested.is_set():
                to_submit = min(batch_size, total_requests - submitted)
                for i in range(submitted, submitted + to_submit):
                    futures.append(exe.submit(task, i))
                submitted += to_submit

                # Process completed futures as they finish to avoid memory growth
                for fut in as_completed(list(futures)):
                    try:
                        success, status_code, elapsed, error = fut.result()
                    except Exception as e:
                        success, status_code, elapsed, error = False, None, 0.0, str(e)
                    with metrics_lock:
                        if success:
                            success_count += 1
                            latencies.append(elapsed)
                            if status_code is not None:
                                statuses[status_code] += 1
                        else:
                            failure_count += 1
                    if pbar.total is not None:
                        pbar.update(1)
                    # remove processed futures from list
                    try:
                        futures.remove(fut)
                    except ValueError:
                        pass

                # small sleep to yield
                if stop_requested.is_set():
                    break
                time.sleep(0.01)
    except KeyboardInterrupt:
        stop_requested.set()
        pbar.close()
        print("\nInterrupted by user; summarizing partial results...", file=sys.stderr)
    finally:
        pbar.close()

    test_duration = time.perf_counter() - test_start
    total_done = success_count + failure_count
    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0
    rps = total_done / test_duration if test_duration > 0 else 0.0
    # Average Concurrent Users = RPS * Average Latency (Little's Law)
    avg_concurrent_users = rps * avg_latency
    success_rate = (success_count / total_done * 100) if total_done > 0 else 0.0

    metrics = {
        "requested": total_requests,
        "completed": total_done,
        "success": success_count,
        "failure": failure_count,
        "success_rate": success_rate,
        "statuses": dict(statuses),
        "avg_latency_s": avg_latency,
        "min_latency_s": min_latency,
        "max_latency_s": max_latency,
        "duration_s": test_duration,
        "rps": rps,
        "avg_concurrent_users": avg_concurrent_users,
    }

    summary = [
        "\nStress test summary:",
        f"  Target URL:  {url}",
        f"  Configured Concurrency: {concurrency} (Simulated Users)",
        f"  Requested:   {total_requests}",
        f"  Completed:   {total_done}",
        f"  Success:     {success_count} ({success_rate:.1f}%)",
        f"  Failure:     {failure_count}",
        f"  Status codes: {dict(statuses)}",
        f"  Duration:    {test_duration:.2f}s",
        f"  Requests/s:  {rps:.2f}",
        f"  Latency (s): avg={avg_latency:.4f} min={min_latency:.4f} max={max_latency:.4f}",
        f"  Estimated Avg. Concurrent Users: {avg_concurrent_users:.2f}"
    ]

    summary_text = "\n".join(summary)
    print(summary_text)

    if save_report:
        from datetime import datetime
        filename = f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(filename, "w") as f:
            f.write(summary_text)
            f.write("\n")
        print(f"\nReport saved to: {filename}")

    return metrics


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multithreaded HTTP stress test with progress bar (tqdm)")
    p.add_argument("--url", "-u", default=os.environ.get("STRESS_TARGET_URL", DEFAULT_URL), help="Target URL to hit")
    p.add_argument("--requests", "-r", type=int, default=int(os.environ.get("STRESS_TOTAL_REQUESTS", TOTAL_REQUESTS)), help="Total number of requests to send")
    p.add_argument("--concurrency", "-c", type=int, default=int(os.environ.get("STRESS_CONCURRENCY", DEFAULT_CONCURRENCY)), help="Number of concurrent worker threads")
    p.add_argument("--timeout", "-t", type=float, default=10.0, help="Per-request timeout in seconds")
    p.add_argument("--method", "-m", default="GET", help="HTTP method to use")
    p.add_argument("--paranoid", action="store_true", help="Run in paranoid mode: push the system using max CPU concurrency until interrupted or --max-requests is reached")
    p.add_argument("--max-requests", type=int, default=0, help="Optional cap for paranoid mode; 0 means unlimited until interrupted")
    p.add_argument("--report", action="store_true", help="Save the test summary to a timestamped .log file")
    return p.parse_args()


def main():
    args = parse_args()
    if args.requests <= 0:
        print("--requests must be > 0", file=sys.stderr)
        sys.exit(2)
    if args.concurrency <= 0:
        print("--concurrency must be > 0", file=sys.stderr)
        sys.exit(2)

    if args.paranoid:
        cpu_count = os.cpu_count() or 1
        concurrency = cpu_count
        total_requests = args.max_requests if args.max_requests > 0 else 10 ** 12
        print(f"Running in PARANOID mode: concurrency={concurrency}, max_requests={'unlimited' if args.max_requests==0 else total_requests}")
        try:
            run_stress_test(
                url=args.url, 
                total_requests=total_requests, 
                concurrency=concurrency, 
                method=args.method, 
                timeout=args.timeout,
                save_report=args.report
            )
        except KeyboardInterrupt:
            print("\nParanoid run interrupted by user.")
    else:
        run_stress_test(
            url=args.url, 
            total_requests=args.requests, 
            concurrency=args.concurrency, 
            method=args.method, 
            timeout=args.timeout,
            save_report=args.report
        )


if __name__ == "__main__":
    main()
