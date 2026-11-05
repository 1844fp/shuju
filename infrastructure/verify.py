"""Read-only smoke test; does not import data into an existing service."""
import argparse, json, urllib.request
parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()
for path in ("health", "ready", "metrics/finance", "imports"):
    with urllib.request.urlopen(args.url + "/api/v1/" + path, timeout=10) as response:
        data = json.load(response)
        assert response.status == 200
        print(path, "OK", "rows=" + str(len(data)) if isinstance(data, list) else data)
