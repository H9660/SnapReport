#!/usr/bin/env python3
"""
SnapReport – Market Report PDF Generator
Generates a branded monthly market report for any US zip code.
Data is deterministically simulated from the zip code (reproducible/demo-safe).
In production: replace _get_market_data() with real API calls.
"""

import sys
import json
import hashlib
import random
import io
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─── Brand colours ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0B1F3A")
TEAL   = colors.HexColor("#00A896")
GOLD   = colors.HexColor("#F4A900")
LIGHT  = colors.HexColor("#F7F9FC")
MID    = colors.HexColor("#DDE4EE")
TEXT   = colors.HexColor("#1A2B45")
MUTED  = colors.HexColor("#6B7C93")

PAGE_W, PAGE_H = letter


# ─── Deterministic market data from zip code ──────────────────────────────────

def _seed(zip_code: str, offset: int = 0) -> random.Random:
    h = int(hashlib.md5((zip_code + str(offset)).encode()).hexdigest(), 16)
    return random.Random(h)

def _get_market_data(zip_code: str, agent_name: str, month: str) -> dict:
    r = _seed(zip_code)

    # Base median price: $300k–$1.8M depending on zip numerics
    base = 300_000 + (int(zip_code) % 90000) * 16
    med_price = round(base / 1000) * 1000

    # Monthly price history (12 months)
    prices = [med_price]
    for _ in range(11):
        prices.append(int(prices[-1] * r.uniform(0.985, 1.025)))
    prices = prices[::-1]  # oldest first

    # Stats
    dom   = r.randint(8, 45)          # days on market
    l2s   = round(r.uniform(0.96, 1.06), 3)  # list-to-sale ratio
    inv   = round(r.uniform(0.8, 4.2), 1)    # months supply
    sold  = r.randint(22, 180)        # homes sold
    new_l = r.randint(18, 220)        # new listings

    yoy   = round((prices[-1] - prices[0]) / prices[0] * 100, 1)

    # Neighbourhood highlights
    neighb = {
        "name": _zip_to_city(zip_code),
        "walkability": r.randint(52, 98),
        "school_rating": round(r.uniform(5.5, 9.8), 1),
        "crime_index": r.choice(["Low", "Low–Moderate", "Moderate"]),
        "new_permits": r.randint(3, 28),
    }

    return {
        "zip_code": zip_code,
        "city": _zip_to_city(zip_code),
        "month": month,
        "agent_name": agent_name,
        "med_price": med_price,
        "med_price_str": f"${med_price:,.0f}",
        "prices": prices,       # list of 12 ints, oldest→newest
        "dom": dom,
        "l2s": l2s,
        "l2s_str": f"{l2s:.1%}",
        "inv": inv,
        "sold": sold,
        "new_listings": new_l,
        "yoy": yoy,
        "yoy_str": f"{'+'if yoy>=0 else ''}{yoy}%",
        "neighb": neighb,
        "market_temp": "Hot" if dom < 18 else ("Warm" if dom < 30 else "Neutral"),
    }

CITY_MAP = {
    "9": "Los Angeles, CA", "1": "New York, NY", "3": "Miami, FL",
    "6": "Chicago, IL", "7": "Dallas, TX", "8": "Seattle, WA",
    "4": "Phoenix, AZ", "2": "Boston, MA", "5": "Denver, CO", "0": "Portland, OR",
}
def _zip_to_city(z: str) -> str:
    return CITY_MAP.get(z[0], "Metro Area, US")


# ─── Chart generation ─────────────────────────────────────────────────────────

def _price_chart(prices: list, zip_code: str) -> io.BytesIO:
    months = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
              "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    fig, ax = plt.subplots(figsize=(6.2, 2.6), facecolor="none")

    x = np.arange(len(months))
    # Gradient fill
    ax.fill_between(x, prices, alpha=0.12, color="#00A896")
    ax.plot(x, prices, color="#00A896", linewidth=2.2, marker="o",
            markersize=4, markerfacecolor="#F4A900", markeredgewidth=0)

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=8, color="#6B7C93")
    ax.tick_params(axis="y", labelsize=8, colors="#6B7C93")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1e3:.0f}k"))
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#DDE4EE")
    ax.grid(axis="y", color="#DDE4EE", linewidth=0.6, linestyle="--")
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                transparent=True, pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


def _gauge_chart(value: int, label: str, color: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(1.6, 1.0), subplot_kw={"aspect": "equal"},
                           facecolor="none")
    theta1, theta2 = 180, 180 - (value / 100 * 180)
    wedge = mpatches.Wedge((0.5, 0.1), 0.38, theta2, theta1,
                           width=0.12, facecolor=color, edgecolor="none")
    bg    = mpatches.Wedge((0.5, 0.1), 0.38, 0, 180,
                           width=0.12, facecolor="#DDE4EE", edgecolor="none", zorder=0)
    ax.add_patch(bg)
    ax.add_patch(wedge)
    ax.text(0.5, 0.14, str(value), ha="center", va="center",
            fontsize=13, fontweight="bold", color="#0B1F3A")
    ax.text(0.5, -0.08, label, ha="center", va="center",
            fontsize=6.5, color="#6B7C93")
    ax.set_xlim(0, 1); ax.set_ylim(-0.2, 0.6)
    ax.axis("off")
    fig.patch.set_alpha(0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


# ─── PDF Canvas callbacks (header / footer) ───────────────────────────────────

class _PageDeco(canvas.Canvas):
    def __init__(self, filename, data, **kw):
        super().__init__(filename, **kw)
        self._data = data
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_page(i + 1, num_pages)
            super().showPage()
        super().save()

    def _draw_page(self, page_num, total):
        d = self._data
        if page_num == 1:
            # Full navy header band
            self.setFillColor(NAVY)
            self.rect(0, PAGE_H - 1.35 * inch, PAGE_W, 1.35 * inch, fill=1, stroke=0)
            # Teal accent stripe
            self.setFillColor(TEAL)
            self.rect(0, PAGE_H - 1.35 * inch, 0.22 * inch, 1.35 * inch, fill=1, stroke=0)
            # Brand name
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 22)
            self.drawString(0.45 * inch, PAGE_H - 0.72 * inch, "Snap")
            self.setFillColor(GOLD)
            self.drawString(0.45 * inch + self.stringWidth("Snap","Helvetica-Bold",22),
                            PAGE_H - 0.72 * inch, "Report")
            # Tagline
            self.setFillColor(MID)
            self.setFont("Helvetica", 8)
            self.drawString(0.45 * inch, PAGE_H - 0.95 * inch,
                            "Monthly Market Intelligence  ·  Powered by Snaphomz")
            # Right side: agent + month
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 9)
            txt = d["agent_name"]
            self.drawRightString(PAGE_W - 0.4 * inch, PAGE_H - 0.70 * inch, txt)
            self.setFont("Helvetica", 8)
            self.setFillColor(MID)
            self.drawRightString(PAGE_W - 0.4 * inch, PAGE_H - 0.88 * inch,
                                 d["month"] + "  ·  " + d["zip_code"])
        else:
            # Thin header on subsequent pages
            self.setFillColor(NAVY)
            self.rect(0, PAGE_H - 0.42 * inch, PAGE_W, 0.42 * inch, fill=1, stroke=0)
            self.setFillColor(TEAL)
            self.rect(0, PAGE_H - 0.42 * inch, 0.22 * inch, 0.42 * inch, fill=1, stroke=0)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 9)
            self.drawString(0.45 * inch, PAGE_H - 0.27 * inch,
                            f"SnapReport  ·  {d['zip_code']}  ·  {d['month']}")

        # Footer
        self.setFillColor(NAVY)
        self.rect(0, 0, PAGE_W, 0.38 * inch, fill=1, stroke=0)
        self.setFillColor(MID)
        self.setFont("Helvetica", 7)
        self.drawString(0.45 * inch, 0.14 * inch,
                        f"© Snaphomz  ·  snaphomz.com  ·  Confidential – prepared for {d['agent_name']}")
        self.setFont("Helvetica", 7)
        self.drawRightString(PAGE_W - 0.4 * inch, 0.14 * inch,
                             f"Page {page_num} of {total}")
        # Teal bottom accent
        self.setFillColor(TEAL)
        self.rect(0, 0.36 * inch, PAGE_W, 0.022 * inch, fill=1, stroke=0)


# ─── Styles ───────────────────────────────────────────────────────────────────

def _styles():
    S = lambda name, **kw: ParagraphStyle(name, **kw)
    return {
        "section":  S("section",  fontName="Helvetica-Bold", fontSize=11,
                      textColor=NAVY,  spaceAfter=6, spaceBefore=14,
                      borderPad=0, leading=14),
        "body":     S("body",     fontName="Helvetica",      fontSize=9,
                      textColor=TEXT, spaceAfter=4, leading=13),
        "label":    S("label",    fontName="Helvetica",      fontSize=7.5,
                      textColor=MUTED, leading=10),
        "big_num":  S("bignum",   fontName="Helvetica-Bold", fontSize=26,
                      textColor=TEAL, leading=30),
        "sub":      S("sub",      fontName="Helvetica",      fontSize=8,
                      textColor=MUTED, leading=10, spaceAfter=2),
        "caption":  S("caption",  fontName="Helvetica",      fontSize=7.5,
                      textColor=MUTED, alignment=TA_CENTER),
        "highlight":S("hl",       fontName="Helvetica-Bold", fontSize=9,
                      textColor=TEXT, leading=13),
        "tag_hot":  S("hot",      fontName="Helvetica-Bold", fontSize=9,
                      textColor=colors.white, backColor=TEAL,
                      borderPad=2, leading=14),
    }


# ─── PDF build ────────────────────────────────────────────────────────────────

def generate_pdf(zip_code: str, agent_name: str, output_path: str,
                 month: str = None) -> str:
    if not month:
        month = datetime.now().strftime("%B %Y")

    data = _get_market_data(zip_code, agent_name, month)
    st   = _styles()

    def make_canvas(filename, **kw):
        return _PageDeco(filename, data, **kw)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=1.55 * inch,
        bottomMargin=0.65 * inch,
        canvasmaker=make_canvas,
    )

    story = []
    add   = story.append

    # ── Hero section ──────────────────────────────────────────────────────────
    add(Paragraph(f"Market Report — {data['city']} ({zip_code})", st["section"]))
    add(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=10))

    # KPI row: 4 stat boxes
    def kpi_cell(label, value, note=""):
        return [
            Paragraph(value, st["big_num"]),
            Paragraph(label, st["sub"]),
            Paragraph(note, st["label"]),
        ]

    temp_color = {"Hot": "#E63B2E", "Warm": "#F4A900", "Neutral": "#6B7C93"}[data["market_temp"]]
    kpi_data = [[
        kpi_cell("Median Sale Price", data["med_price_str"],
                 f"YoY {data['yoy_str']}"),
        kpi_cell("Days on Market", str(data["dom"]),
                 "Avg. days to go pending"),
        kpi_cell("Homes Sold", str(data["sold"]),
                 "This month"),
        kpi_cell("Months of Supply", str(data["inv"]),
                 "Inventory level"),
    ]]
    kpi_table = Table(kpi_data, colWidths=["25%"] * 4,
                      rowHeights=None)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT]),
        ("BOX",       (0, 0), (-1, -1), 0.5, MID),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, MID),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    add(kpi_table)
    add(Spacer(1, 14))

    # ── Price trend chart ─────────────────────────────────────────────────────
    add(Paragraph("12-Month Median Price Trend", st["section"]))
    chart_buf = _price_chart(data["prices"], zip_code)
    chart_img = RLImage(chart_buf, width=6.7 * inch, height=2.5 * inch)
    add(chart_img)
    add(Paragraph(f"Jul–Jun  |  {data['city']} ZIP {zip_code}  ·  Source: Snaphomz MLS Analytics",
                  st["caption"]))
    add(Spacer(1, 14))

    # ── Market summary table ──────────────────────────────────────────────────
    add(Paragraph("Key Market Metrics", st["section"]))
    rows = [
        ["Metric", "This Month", "YoY Change", "Signal"],
        ["Median Sale Price",   data["med_price_str"],
         data["yoy_str"],
         "Rising" if data["yoy"] > 2 else ("Stable" if data["yoy"] > -2 else "Declining")],
        ["Avg. Days on Market", str(data["dom"]) + " days",
         f"{random.Random(zip_code).randint(-8, 8):+d} days", data["market_temp"]],
        ["List-to-Sale Ratio",  data["l2s_str"], "—",
         "Above ask" if data["l2s"] > 1 else "At/below ask"],
        ["New Listings",        str(data["new_listings"]), "—", "Active supply"],
        ["Months of Supply",    str(data["inv"]),
         f"{random.Random(zip_code+'inv').uniform(-0.5, 0.5):+.1f} mo.",
         "Seller's market" if data["inv"] < 2 else ("Balanced" if data["inv"] < 4 else "Buyer's market")],
    ]
    metric_table = Table(rows, colWidths=[2.2*inch, 1.5*inch, 1.4*inch, 2.0*inch])
    metric_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT]),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR",     (0, 1), (-1, -1), TEXT),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        # Highlight signal column
        ("TEXTCOLOR",     (3, 1), (3, -1), TEAL),
        ("FONTNAME",      (3, 1), (3, -1), "Helvetica-Bold"),
    ]))
    add(metric_table)
    add(Spacer(1, 16))

    # ── Neighbourhood scorecard ───────────────────────────────────────────────
    add(Paragraph("Neighbourhood Scorecard", st["section"]))
    nb = data["neighb"]
    walk_buf  = _gauge_chart(nb["walkability"], "Walk Score",  "#00A896")
    # school score → /10 → /100
    sch_val   = int(nb["school_rating"] * 10)
    sch_buf   = _gauge_chart(sch_val, "School Rating", "#F4A900")

    gauge_row = [[
        RLImage(walk_buf, 1.4*inch, 0.88*inch),
        RLImage(sch_buf,  1.4*inch, 0.88*inch),
        [
            Paragraph("Crime Level", st["label"]),
            Paragraph(nb["crime_index"], st["highlight"]),
            Spacer(1, 6),
            Paragraph("New Build Permits (30d)", st["label"]),
            Paragraph(str(nb["new_permits"]), st["highlight"]),
        ],
        [
            Paragraph("Market Temperature", st["label"]),
            Paragraph(
                f'<font color="{"#E63B2E" if data["market_temp"]=="Hot" else "#F4A900" if data["market_temp"]=="Warm" else "#6B7C93"}">'
                f'{data["market_temp"]}</font>', st["highlight"]),
            Spacer(1, 6),
            Paragraph("List-to-Sale", st["label"]),
            Paragraph(data["l2s_str"], st["highlight"]),
        ],
    ]]
    nb_table = Table(gauge_row, colWidths=[1.55*inch]*4)
    nb_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT),
        ("BOX",          (0, 0), (-1, -1), 0.5, MID),
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, MID),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    add(nb_table)
    add(Spacer(1, 18))

    # ── Agent note / market narrative ─────────────────────────────────────────
    add(Paragraph("Market Commentary", st["section"]))
    narrative = _build_narrative(data)
    add(Paragraph(narrative, st["body"]))
    add(Spacer(1, 14))

    # ── CTA footer block ──────────────────────────────────────────────────────
    cta_data = [[
        Paragraph(
            f"<b>Ready to make your move in {data['city']}?</b><br/>"
            f"Contact {data['agent_name']} — your local market expert — "
            f"or search live listings at <font color='#00A896'>snaphomz.com/{zip_code}</font>",
            ParagraphStyle("cta", fontName="Helvetica", fontSize=9,
                           textColor=colors.white, leading=14)
        )
    ]]
    cta_table = Table(cta_data, colWidths=[PAGE_W - 1.1*inch])
    cta_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",   (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    add(cta_table)

    doc.build(story)
    return output_path


def _build_narrative(d: dict) -> str:
    city  = d["city"]
    month = d["month"]
    price = d["med_price_str"]
    dom   = d["dom"]
    yoy   = d["yoy_str"]
    inv   = d["inv"]
    temp  = d["market_temp"]
    l2s   = d["l2s"]

    tempo_phrase = {
        "Hot": "Buyer competition remains fierce",
        "Warm": "Demand continues to outpace supply",
        "Neutral": "The market has found a stable equilibrium",
    }[temp]

    supply_note = (
        "With only {inv} months of supply, sellers hold significant leverage."
        if inv < 2 else
        f"At {inv} months of supply, conditions are broadly balanced."
        if inv < 4 else
        f"Inventory at {inv} months gives buyers room to negotiate."
    ).format(inv=inv)

    l2s_note = (
        f"The average home sold for {(l2s-1)*100:.1f}% above list price, "
        "signalling that multiple-offer situations remain common."
        if l2s > 1.005 else
        "Homes are closing near their list price, reflecting realistic pricing by sellers."
    )

    return (
        f"As of {month}, the {city} market continues to demonstrate resilience. "
        f"The median sale price of {price} reflects a year-over-year change of {yoy}, "
        f"while properties are spending an average of {dom} days on market. "
        f"{tempo_phrase}. {supply_note} {l2s_note} "
        f"New building permit activity in the area suggests steady long-term demand, "
        f"and school quality ratings remain a key driver of price premiums in this zip code. "
        f"For sellers, now is a strong window to price competitively and leverage "
        f"Snaphomz's AI-assisted staging tools. Buyers should move quickly on well-priced "
        f"properties — consult {d['agent_name']} for a personalised strategy."
    )


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate SnapReport PDF")
    p.add_argument("zip_code", help="US ZIP code")
    p.add_argument("agent_name", help="Agent full name")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--month", default=None, help="Month label e.g. 'June 2026'")
    args = p.parse_args()
    out = generate_pdf(args.zip_code, args.agent_name, args.output, args.month)
    print(json.dumps({"status": "ok", "path": out}))
