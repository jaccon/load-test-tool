# Load Test Tool

A powerful, multithreaded HTTP stress test script with progress tracking and performance analytics.

## Features

- **Multithreaded Execution**: Uses Python's `ThreadPoolExecutor` for high performance.
- **Connection Pooling**: Efficiently manages connections using `requests.Session` per worker thread.
- **Real-time Progress**: Visual progress bar using `tqdm`.
- **Performance Metrics**: Calculates RPS (Requests Per Second), average latency, and estimated concurrent users.
- **Reporting**: Generates timestamped log files with full test summaries.
- **Paranoid Mode**: Maximizes concurrency to CPU core count for intensive testing.

## Installation

Ensure you have Python 3 installed, then install the required dependencies:

```sh
pip install requests tqdm
```

## Basic Usage

The script is now named `load-test-tool.py`. You can run it with default values or override them via CLI flags.

### CLI Examples

```sh
# Basic test with defaults
python3 load-test-tool.py

# Custom URL, requests, and concurrency
python3 load-test-tool.py --url https://example.com --requests 500 --concurrency 50

# Save results to a report file
python3 load-test-tool.py --url https://example.com --requests 200 --report

# Run in Paranoid Mode (Max CPU threads, unlimited/max requests)
python3 load-test-tool.py --url https://example.com --paranoid --max-requests 1000
```

### CLI Flags

- `--url`, `-u`: Target URL (Default: `https://example.com`)
- `--requests`, `-r`: Total number of requests to send (Default: `100`)
- `--concurrency`, `-c`: Number of simulated users / concurrent threads (Default: `10`)
- `--timeout`, `-t`: Per-request timeout in seconds (Default: `10.0`)
- `--method`, `-m`: HTTP method (GET, POST, etc.) (Default: `GET`)
- `--report`: Save the test summary to a timestamped `.log` file.
- `--paranoid`: Run with maximum concurrency based on CPU cores.
- `--max-requests`: Optional cap for requests in paranoid mode.

## Environment Variables

You can also configure the tool using environment variables (CLI flags will always override these):

```sh
export STRESS_TOTAL_REQUESTS=1000
export STRESS_CONCURRENCY=100
export STRESS_TARGET_URL=https://example.com
python3 load-test-tool.py
```

## Understanding the Results

At the end of each test, you'll receive a summary like this:

- **Configured Concurrency**: The number of simulated users (threads) you requested.
- **Success Rate**: Percentage of requests that returned successfully.
- **Requests/s**: The throughput (vibe) of the server.
- **Latency (s)**: Average, minimum, and maximum response times.
- **Estimated Avg. Concurrent Users**: Calculated based on Little's Law ($RPS \times Latency$), representing the actual effective load during the test.

## Notes

- **Responsible Usage**: Only test endpoints you own or have explicit permission to stress test.
- **Resource Monitoring**: For extremely high concurrency, monitor your local machine's CPU and memory usage.
- **Connection Limits**: Ensure your OS allows a high number of open file descriptors if you plan to use very high concurrency.

---
Created and maintained by [jaccon](https://github.com/jaccon).
