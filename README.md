# SnapReport 📄

**Automated monthly market report PDFs for real estate agents — powered by Snaphomz.**

Enter a ZIP code, hit Generate, get a fully branded, data-rich PDF in under 90 seconds. No AI credits. No third-party subscriptions. No manual work.

---

## What It Does

SnapReport turns raw market data into a polished, co-branded PDF that agents send to their sphere of influence every month. Each report contains:

- **4 KPI stat boxes** — median sale price, days on market, homes sold, months of supply
- **12-month price trend chart** — line chart with YoY change calculation
- **Full metrics table** — list-to-sale ratio, new listings, market signal labels
- **Neighbourhood scorecard** — Walk Score gauge, school rating, crime level, new permit count
- **Plain-English market commentary** — reads like an analyst wrote it
- **Snaphomz co-branding** — agent name on every page, CTA linking to `snaphomz.com/{zip}`

Every PDF is deterministically generated from the ZIP code, so the same inputs always produce the same report — consistent, reproducible, demo-safe.

---

## Project Structure

```
snapreport/
├── generate_report.py   # PDF engine — all charts, layout, data, branding
├── server.py            # Lightweight HTTP server (stdlib only, no framework)
├── index.html           # Frontend — form, ZIP tag input, download UI
├── requirements.txt     # Python dependencies
├── Procfile             # For Railway / Render deployment
└── README.md            # You are here
```

---

## Quickstart

### Prerequisites

- Python 3.9+
- pip

### Install & Run

```bash
# 1. Clone or download the project
git clone https://github.com/your-org/snapreport.git
cd snapreport

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python server.py

# 4. Open in browser
# http://localhost:7654
```

The app is now running. Enter a ZIP code, an agent name, and click **Generate PDF Report**.

---

## Dependencies

```
reportlab==4.2.0    # PDF generation and layout engine
matplotlib==3.9.0   # Chart rendering (price trend, gauge charts)
```

Both are pure-Python and install without any system libraries.

Full `requirements.txt`:

```
reportlab
matplotlib
```

---

## How to Generate a PDF from the CLI

You can generate reports directly without the web interface:

```bash
python generate_report.py <ZIP_CODE> "<AGENT_NAME>" <OUTPUT_PATH> [--month "Month YYYY"]
```

**Examples:**

```bash
# Beverly Hills, June report for Sarah Chen
python generate_report.py 90210 "Sarah Chen" ./reports/90210_june.pdf --month "June 2026"

# New York, default month (current)
python generate_report.py 10001 "Marcus Williams" ./reports/10001.pdf

# Multiple ZIPs via a shell loop
for ZIP in 90210 10001 77002 60601 98101; do
  python generate_report.py $ZIP "Your Agent" ./reports/${ZIP}.pdf --month "June 2026"
done
```

Output is a single self-contained PDF, typically 35–45 KB.

---

## API Reference

The server exposes one endpoint.

### `POST /api/generate`

Generates a PDF report and returns it as a binary stream.

**Request body (JSON):**

| Field | Type | Required | Description |
|---|---|---|---|
| `zip_code` | string | Yes | 5-digit US ZIP code |
| `agent_name` | string | No | Agent display name (default: "Your Agent") |
| `month` | string | No | Month label e.g. `"June 2026"` (default: current month) |

**Example request:**

```bash
curl -X POST http://localhost:7654/api/generate \
  -H "Content-Type: application/json" \
  -d '{"zip_code": "90210", "agent_name": "Sarah Chen", "month": "June 2026"}' \
  --output SnapReport_90210.pdf
```

**Success response:**

- Status: `200 OK`
- Content-Type: `application/pdf`
- Body: raw PDF bytes
- Header: `Content-Disposition: attachment; filename="SnapReport_90210.pdf"`

**Error response:**

```json
{ "error": "Please enter a valid 5-digit ZIP code." }
```

---

## Deploying to Production

### Railway (recommended — free tier, ~5 minutes)

1. Push the project to a GitHub repository
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select your repo — Railway auto-detects Python
4. Set the start command to `python server.py` (or use the included `Procfile`)
5. Railway injects `PORT` automatically — the server reads it via `os.environ.get("PORT", 7654)`
6. Your app gets a public URL like `https://snapreport-production.up.railway.app`

**Procfile** (already included):

```
web: python server.py
```

### Render

Same steps as Railway. Go to [render.com](https://render.com) → New Web Service → connect GitHub repo → set Build Command to `pip install -r requirements.txt` and Start Command to `python server.py`.

### Fly.io

```bash
# Install flyctl, then:
fly launch
fly deploy
```

### Running on a local network (for hackathon demos)

Find your machine's local IP address:

```bash
# macOS / Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

Then anyone on the same Wi-Fi can access `http://192.168.x.x:7654`.

---

## Data Layer

### Current implementation (hackathon / demo)

Market data is **deterministically simulated** from the ZIP code using a seeded PRNG. The same ZIP always returns the same stats — there are no random fluctuations between runs. This makes demos reliable and reproducible.

The seed function:

```python
def _seed(zip_code: str, offset: int = 0) -> random.Random:
    h = int(hashlib.md5((zip_code + str(offset)).encode()).hexdigest(), 16)
    return random.Random(h)
```

All market metrics — median price, days on market, list-to-sale ratio, inventory, sold count, new listings — are derived from this seed and scaled to realistic ranges.

### Upgrading to real data (production path)

Replace the `_get_market_data()` function in `generate_report.py` with real API calls. Suggested free/low-cost sources:

| Data Point | Source | Notes |
|---|---|---|
| Median sale price, comps | [RealEstateAPI.com](https://realestateapi.com) | Paid, good MLS coverage |
| Historical home values | [Zillow Research CSVs](https://www.zillow.com/research/data/) | Free, bulk download |
| Market stats (DOM, inventory) | [Redfin Data Center](https://www.redfin.com/news/data-center/) | Free CSV downloads |
| Building permits | [Census Building Permits API](https://www.census.gov/construction/bps/) | Free, no key needed |
| Walk Score | [Walk Score API](https://www.walkscore.com/professional/api.php) | Freemium |
| School ratings | [GreatSchools API](https://www.greatschools.org/gk/api/) | Free tier available |
| Crime data | [SpotCrime API](https://spotcrime.com/data) | Freemium |

The function signature to implement:

```python
def _get_market_data(zip_code: str, agent_name: str, month: str) -> dict:
    # Return a dict matching the schema used by generate_pdf()
    # See the existing implementation for the full expected structure
    ...
```

---

## Branding & Customisation

### Colours

All brand colours are defined as constants at the top of `generate_report.py`:

```python
NAVY   = colors.HexColor("#0B1F3A")   # Primary background
TEAL   = colors.HexColor("#00A896")   # Accent / highlights
GOLD   = colors.HexColor("#F4A900")   # Brand name accent
LIGHT  = colors.HexColor("#F7F9FC")   # Card backgrounds
MID    = colors.HexColor("#DDE4EE")   # Borders / dividers
TEXT   = colors.HexColor("#1A2B45")   # Body text
MUTED  = colors.HexColor("#6B7C93")   # Labels / secondary text
```

### Adding an agent logo / photo

The `_PageDeco` class handles all canvas-level header/footer drawing. To add an agent photo:

```python
# In _draw_page(), inside the page_num == 1 block:
from reportlab.lib.utils import ImageReader
logo = ImageReader("path/to/agent_photo.jpg")
self.drawImage(logo, PAGE_W - 1.2*inch, PAGE_H - 1.1*inch,
               width=0.7*inch, height=0.7*inch, mask='auto')
```

### Changing the report colour scheme

Edit the hex values in the constants block. All charts, tables, and callouts inherit from these variables — there is no hardcoded colour elsewhere in the file.

---

## Roadmap

Features intentionally left out of the MVP (known scope decisions):

| Feature | Why deferred |
|---|---|
| Real MLS API integration | Requires paid API keys; seeded data is sufficient to demo the PDF quality and layout |
| Agent photo upload | Needs file handling in the frontend and server; straightforward to add |
| Scheduled monthly delivery | Requires a job queue (Celery / APScheduler) and email provider (SendGrid); clean second sprint |
| Agent CRM / contact list | Database layer (Postgres) needed; out of scope for a 1-hour build |
| PDF email delivery | SendGrid integration, ~1 day of work |
| White-label custom domains | Platform-level feature, not MVP |
| Multiple market data sources | API keys and ETL pipeline; production-phase work |

---

## Why SnapReport for Snaphomz

Every PDF sent to a homeowner's inbox contains:

- The agent's name — keeping them top-of-mind
- A direct `snaphomz.com/{zip}` call-to-action — driving organic traffic back to listings
- Snaphomz co-branding on every page — building platform brand authority

An agent who sends 200 contacts a monthly report generates 200 co-branded Snaphomz impressions per month, at zero acquisition cost. At scale across Snaphomz's agent network, this becomes a significant and compounding organic channel.

---

## Hackathon Notes

Built for **Snaphomz Hackathon 2.0** — Project #10 from the project menu.

**What was built:** Full-stack web app — Python PDF engine with branded charts and layout, lightweight HTTP server, polished React-style frontend with multi-ZIP input and instant PDF download.

**What was left out (intentional):** Real MLS data API calls (blocked in sandbox; seeded simulation used instead), scheduled email delivery, agent photo upload, database persistence.

**Architecture decisions:**
- `reportlab` chosen over WeasyPrint for PDF generation — no system dependency on a headless browser, faster, and more reliable in restricted environments
- `matplotlib` for charts — deterministic output, no JS runtime needed, embeds cleanly into reportlab via BytesIO
- Stdlib `http.server` for the backend — zero framework dependencies, nothing to install beyond `requirements.txt`, trivially portable
- Seeded PRNG for data — makes the demo perfectly reproducible while keeping the full PDF pipeline exercisable without any API keys

---

## Licence

Confidential — Snaphomz internal hackathon project. Do not distribute.