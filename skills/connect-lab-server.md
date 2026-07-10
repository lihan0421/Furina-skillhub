---
name: connect-lab-server
description: Connect to a lab server via SSH using plink. Use when asked to connect to, SSH into, or run commands on the lab server.
---

# Lab Server SSH Connection

**Prerequisites:** Your institution's VPN must be active (if the server is only reachable over VPN).

## Server Details

This is a template - fill in your own server's details locally (not tracked
in this repo):

| Field    | Value              |
|----------|--------------------|
| Host     | *(set locally)*    |
| Port     | *(set locally)*    |
| User     | *(set locally)*    |
| Password | *(set locally)*    |
| Hostname | *(set locally)*    |

## How to Connect

**Run a single command:**

```powershell
$proc = Start-Process -FilePath "C:\Program Files\PuTTY\plink.exe" `
  -ArgumentList "-ssh -P <PORT> -l <USER> -pw <PASSWORD> -hostkey <HOST_KEY_FINGERPRINT> <HOST> `"<YOUR COMMAND>`"" `
  -NoNewWindow -PassThru `
  -RedirectStandardOutput "$env:TEMP\plink_out.txt" `
  -RedirectStandardError "$env:TEMP\plink_err.txt"
$proc.WaitForExit(30000)
Get-Content "$env:TEMP\plink_out.txt"
Get-Content "$env:TEMP\plink_err.txt"
```

**Interactive terminal (run in your own terminal):**

```
ssh <USER>@<HOST> -p <PORT>
# password: (set locally)
```

## Troubleshooting

- **Connection timeout / refused** → Check that your VPN is connected (if applicable).
- **Host key error in batch mode** → Use the `-hostkey <fingerprint>` flag with plink.
- `sshpass` is not available on Windows by default; use plink instead.
