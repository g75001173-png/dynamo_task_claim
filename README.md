# Dynamo Task Claim

Polls the configured Handshake claim endpoint until a task is returned.

## Local Setup

```powershell
python -m pip install -r requirements.txt
Copy-Item claim_request.example.json claim_request.json
python dynamo_claim.py --check
python dynamo_claim.py
```

Populate `claim_request.json` from an authenticated request before running it. The file is
ignored by Git because it contains a live session cookie.

## GitHub Codespaces

Do not commit `claim_request.json`. Store its complete JSON contents as a Codespaces secret:

1. Open the repository's **Settings**.
2. Open **Secrets and variables**, then **Codespaces**.
3. Create a repository secret named `CLAIM_REQUEST_JSON`.
4. Paste the complete contents of your local `claim_request.json` as the value.
5. Create or restart the Codespace so the secret is available.

Inside the Codespace, run:

```bash
python -m pip install -r requirements.txt
python dynamo_claim.py --check
python dynamo_claim.py
```

The script uses the local `claim_request.json` when present and otherwise reads the
`CLAIM_REQUEST_JSON` environment variable. Use the service only from locations and in ways
permitted by its access policies.
