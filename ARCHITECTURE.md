# How Fundprint Works (in plain words)

Fundprint tells you how well your mutual fund money is doing, split by how long you have held it, and whether a simple index fund would have done better.

## The big picture

There are two parts that never touch each other's secrets:

1. **The website** – what you see and use. Your statement stays here.
2. **The daily update** – gets public fund prices so the website can compare.

---

## Part 1: What happens when you use it

```
  YOU                                  YOUR BROWSER
  ───                                  ────────────
  1. Ask your fund registrar
     (CAMS / KFintech) for a
     "Detailed" statement (PDF)
            │
            ▼
  2. Open Fundprint and
     drop the PDF in  ──────────────►  3. Reads the statement
                                          (on your own device)
                                               │
                                               ▼
                                       4. Works out what you
                                          still hold today
                                               │
                                               ▼
                                       5. Groups each purchase by
                                          how long you've held it:
                                          under 1 yr · 1–3 · 3–5 · 5+
                                               │
                                               ▼
                                       6. Works out the yearly return
                                          of each group
                                               │
                                               ▼
                                       7. Asks: "What if the same money
                                          had gone into a Nifty 50
                                          index fund on the same dates?"
                                               │
  9. You read the result  ◄─────────── 8. Shows the comparison
     (percentages only,                   for each group
      no rupee amounts)

  10. Close the tab  ───────────────►  Everything is forgotten.
```

**Key point:** your statement is never sent anywhere. All the work happens inside your own browser. Close the tab and it's gone.

---

## Part 2: How the website stays up to date

```
  Every day, automatically
            │
            ▼
  Collect public fund prices  ──►  Run safety checks  ──►  Anything new?
  (the same prices anyone                                       │
   can look up)                                      ┌──────────┴──────────┐
                                                    No                    Yes
                                                     │                     │
                                                  Do nothing        Rebuild the website
                                                                           │
                                                                           ▼
                                                                  Test it again
                                                                           │
                                                                           ▼
                                                                  Publish the new version
```

Two separate steps are used on purpose: one **builds and tests** the site, a different one **publishes** it. The step that publishes holds the key but runs no project code, which keeps things safe.

---

## What is stored, and where

| Thing | Where it lives | Who can see it |
|---|---|---|
| Your statement | Your browser only, until you close the tab | Only you |
| Public fund prices | Inside the website files | Everyone (it's public data) |
| Visit counter | Umami: anonymised counts of page visits | The site owner |
| Feedback you choose to send | Tally, the form service (name, email and screenshot are optional) | The site owner |

---

## In one line

> You drop in your statement → your browser does all the maths → you see how each batch of money did versus a plain index fund → nothing is kept.
