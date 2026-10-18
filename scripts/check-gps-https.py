#!/usr/bin/env python3
"""Probe the isolated GPS HTTPS proxy with synthetic data, then inspect its logs.

Start the servers/proxy as documented in docs/gps_plans/https-test-environment.md.
The supplied CA is explicitly trusted only by this probe. No real GPS is read.
"""
import argparse
import json
from pathlib import Path
import ssl
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://localhost:8443')
    parser.add_argument('--ca', type=Path, required=True)
    parser.add_argument('--log-dir', type=Path, required=True)
    parser.add_argument('--backend-log', type=Path)
    parser.add_argument('--expect-upstream-down', action='store_true')
    args = parser.parse_args()
    if not args.base_url.startswith('https://'):
        parser.error('An HTTPS origin is required')
    context = ssl.create_default_context(cafile=str(args.ca))
    base = args.base_url.rstrip('/')
    sentinels = ('12.345678', '98.765432')
    nearby = '/api/v1/customer/service-points/nearby'

    def request(path, expected, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(base + path, data=payload,
                                     headers={'Content-Type': 'application/json'})
        try:
            response = urllib.request.urlopen(req, context=context, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            assert response.status == expected, f'Expected HTTP {expected}, got {response.status}'
            body = response.read()
            print(f'PASS HTTPS HTTP {expected}', flush=True)
            return body

    query = '?lat=12.345678&lng=98.765432'
    if args.expect_upstream_down:
        request(nearby + query, 502)
    else:
        request(nearby + query, 200)
        request(nearby + '?lat=112.345678&lng=98.765432', 422)
        # Follows FastAPI's slash redirect; Host must retain the TLS port.
        request(nearby + '/' + query, 200)
        request('/chat', 200)
        request('/maplibre-gl-worker.mjs', 200)
        username = 'https_synthetic_' + uuid.uuid4().hex
        password = 'LocalSyntheticTest!2026'
        request('/api/v1/auth/register', 200, {'username': username, 'password': password})
        auth = json.loads(request('/api/v1/auth/login', 200, {'username': username, 'password': password}))
        assert auth['data']['token'], 'Login did not return a token'

    logs = list(args.log_dir.rglob('*'))
    if args.backend_log:
        logs.append(args.backend_log)
    files = [path for path in logs if path.is_file()]
    assert files, 'No logs found; privacy cannot be verified'
    for path in files:
        contents = path.read_bytes()
        assert not any(value.encode() in contents for value in sentinels), f'Synthetic coordinate found in {path.name}'
    print(f'PASS coordinate absence in {len(files)} supplied log files; tracing is disabled')


if __name__ == '__main__':
    main()
