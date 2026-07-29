# Demo walkthrough

A script for presenting UrbanHeat AI live. Five minutes end to end; each section below is a
stop, with what to click and what to say. Live at
**[urbanheat-mumbai.vercel.app](https://urbanheat-mumbai.vercel.app)**.

**Before you start:** hit [urbanheat-api.onrender.com/health](https://urbanheat-api.onrender.com/health)
a couple of minutes ahead of time — the free-tier backend sleeps after 15 minutes idle and
takes about a minute to wake. A cold start mid-demo looks like a broken app; a warm one
doesn't.

---

## 1. Heat map — the problem, visually

Open the app. It lands on the heat map: every 200m cell across Mumbai, coloured by surface
temperature.

*"This is Mumbai's entire built-up area, ~12,000 cells, each one an independent Land Surface
Temperature reading from Landsat thermal imagery — not modelled, measured."*

Switch layers (LST → NDVI → HVI → Built) to show the same city through different lenses.
Click any cell.

*"Every cell explains itself — this isn't a heatmap you have to interpret, it tells you why
it's hot."* The drawer that opens shows the cell's SHAP attribution: which physical features
(built density, albedo, distance to water) are pushing that specific cell's temperature up or
down, and by how much.

## 2. Analytics — where it's worst, and for whom

Switch to **Analytics**. The hotspot ranking sorts all 24 wards by Heat Vulnerability Index —
not just "hottest," but heat exposure weighted by population and green-cover deficit.

*"Ward B tops the list — small, dense, built-up, high heat and comparatively low population.
Ward L is close behind but carries 600,000+ people — that's the one that actually matters for
where you'd send resources."* This is the difference between a thermometer and a
prioritisation tool.

## 3. Scenario simulator — what happens if you intervene

Switch to **Scenario simulator**. Pick Ward L, leave it on **Greening**, hit **Simulate**.

*"This calls the trained model again, with the ward's vegetation index raised as if it had
been planted — a real inference, not a lookup table."* Point out the map overlay (every cell's
predicted ΔLST) and the disclosed caveat text — the model's own citation for why this number
is trustworthy, and where it stops being one.

Toggle to **Cool roof**, drag coverage — note it never triggers the clamping warning, because
that lever is a cited physical formula, not a model extrapolation past its training data. If
signed in, hit **Save scenario** to show persistence; either way, hit **Download report** to
show the PDF — same numbers, formatted for someone who wasn't in the room.

## 4. Copilot — ask it anything

Switch to **Copilot**. Type a real question: *"Which ward is the hottest and why?"* or
*"What would greening do to Ward B?"*

*"This isn't a canned answer — it's an agent calling the same tools you just used by hand:
get_hotspots, explain_ward, simulate_scenario. What comes back is grounded in this session's
real numbers, cited, not generated from the model's general knowledge of Mumbai."* If the
question touches policy ("what does NDMA recommend for heat waves?"), it retrieves from real
government documents and cites them — show one, if time allows.

## 5. Alerts — the part that runs without you

Switch to **Alerts**. Most days this is empty, deliberately.

*"A scheduled job checks the forecast against Mumbai's heat-wave threshold every morning,
whether or not anyone's looking at the dashboard. An empty feed most days isn't a broken
feature — Mumbai crossing 45°C is genuinely rare, and a system that cried wolf would be worse
than one that's quiet."*

---

## Closing line

*"Every number on every screen traces back to a real dataset, a real trained model, or a
cited source — nothing here is invented to look impressive."* That's the one sentence that
matters more than any individual feature.
