# Security Policy

Fundprint handles mutual fund statements, so security and privacy issues are taken seriously.

## How Fundprint is designed
- Everything runs **in your browser**. There is no server, database or user account.
- Your statement and password are processed **in memory only** and are never uploaded, stored or logged.
- The only outside service the page talks to is **Umami**, for anonymous, data-free usage counts.

So a security issue here usually means something that could break that promise. For example:
- any way statement data, the password or results could leave the browser (network requests, URLs, analytics events, error messages);
- any way that data could persist after the tab is closed (browser storage, caches);
- the published site serving code that differs from this repository;
- a vulnerable dependency that could be exploited in the browser.

## Reporting a vulnerability
**Please don't open a public issue.**

Report it privately through GitHub: go to this repository's **Security** tab and click **"Report a vulnerability"**.

Please include:
- what you found and how to reproduce it (steps, browser, device);
- what could be exposed or affected;
- a suggested fix, if you have one.

**Never include a real statement or personal data.** Use the app's sample data, or describe the issue without real details.

## What to expect
- An acknowledgement within **7 days**.
- An update on the fix or decision within **30 days**.
- Credit in the pull request that fixes it, if you'd like it.

This is a one-person, open-source project, so timelines are best effort, but privacy issues get priority over everything else.

## Supported versions
Only the live version at https://lab.shibaprasadb.com/fundprint (the `main` branch) is supported. Fixes are made there.
