# Dynamo Task Sniper

Async Handshake task sniper using aiohttp — pure API, no browser.

## Setup

```powershell
python -m pip install aiohttp
python dynamo_sniper.py
```

Choose:

1. **Start Polling (Sniper Mode)** – polls available tasks and fires parallel claims.
2. **Test Connection (Available Tasks)** – verifies the session cookie and prints the raw API response.
3. **Test Connection (My Past Tasks)** – lists claimed tasks.

## Notes

- `dynamo_sniper.py` embeds a live session cookie; refresh the `Cookie` header when the
  session expires (copy the fresh cookie values from your browser into `COOKIE`).
- Task claiming uses the `task.claimTask` endpoint with `taskId`, `annotationProjectId`, and
  `claimerId` — set `CLAIMER_ID` to your own value.
- The server may still block requests by network location (`GEO_BLOCKED`); use it only from
  locations and in ways permitted by the service's access policies.