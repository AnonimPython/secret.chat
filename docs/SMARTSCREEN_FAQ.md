# Windows complains about SecretChat.exe? Let's sort it out

A short note for whoever you hand the app to. Read it — no panic.

## Why does Windows show a warning?

Because the app has **no paid code-signing certificate**. Microsoft requires a
certificate (it costs money, ~$100–300/year) for Windows to "trust" a developer
in advance and skip the blue SmartScreen prompt.

Important: **a warning is not a virus.** It simply means "we don't know this
publisher". Windows greets thousands of legitimate free apps the same way.

## What is this app?

- Open source — you can read every line yourself.
- Collects nothing: no accounts, no telemetry, no servers.
- Connects **directly** to the IP you type in.
- All messages are encrypted; chats are wiped when you close the app.

## How to open it

**Option 1 — the blue SmartScreen screen ("Windows protected your PC"):**

1. Click **More info**.
2. Click **Run anyway**.
3. Done.

**Option 2 — the app doesn't run, but there is no screen either:**

1. Right-click `SecretChat.exe` → **Properties**.
2. At the bottom, if there is an **Unblock** checkbox — tick it.
3. **OK**, then run it.

That is a one-time action; after that the app just opens.

## The antivirus still complains (false positive)

It happens: the file was downloaded from the internet and some antivirus got
suspicious. What to do:

1. **Don't delete it right away.** Check: the file is called `SecretChat.exe`,
   it is where you put it, and it came from someone you know.
2. Report the false positive to Microsoft — it is free and actually helps:
   https://www.microsoft.com/en-us/wdsi/filesubmission
   (pick the file, mark it as "not malicious" / false positive).
3. The more people click "Run anyway" and submit, the faster the file builds
   "reputation" and stops being flagged anywhere.

## How to share the file properly

- **Bad:** sending the exe straight through a messenger / email / browser —
  Windows marks it "from the internet" and complains harder.
- **Good:** put it in a **zip archive**, on a USB stick, or in **GitHub
  Releases** — fewer warnings, and on GitHub reputation builds automatically.
- **Best:** the `dist\SecretChat\` folder (standalone build) instead of a single
  file — antiviruses flag it the least.

## Why can't the warning be removed completely?

Full "silent" opening requires an official Microsoft code-signing certificate
(paid). There is no free workaround — any trick (forged signatures, "fake"
certs) only adds trouble: antiviruses will brand the file malicious. So the
honest path is to open it once via "More info → Run anyway".
