# temp_site

Minimal writable bridge for CardspaceExplorer inspection snapshots.

## Run

```bash
export BRIDGE_TOKEN='replace-with-a-long-random-secret'
python3 server.py
```

Defaults to port `8080`.

## Publish from WSL

```bash
curl -s 'http://127.0.0.1:8787/api/v1/inspection?events=20' > /tmp/inspection.json

curl -fS -X PUT \
  -H "Authorization: Bearer $BRIDGE_TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/inspection.json \
  https://YOUR-HOST/api/inspection
```

## Read

- `GET /inspection.json`
- `GET /`
- `GET /health`

Only the upload endpoint requires the bearer token. Keep `BRIDGE_TOKEN` server-side / in WSL only; never put it in the page or repository.
