"""
Xenkloud Pulse — report generator

Takes the raw JSON from xenkloud_pulse_backend.py's /api/summary endpoint
and turns it into a client-ready report: a Markdown file (easy to paste
into an email) and a polished PDF (easy to attach/send).

Setup:
    pip install fpdf2 --break-system-packages

Usage:
    1. Save the /api/summary JSON output to a file, e.g. acme_data.json
    2. Run:
       python xenkloud_pulse_report_generator.py \\
           --data acme_data.json \\
           --client "Acme Inc" \\
           --budget 2800 \\
           --your-name "Jordan" \\
           --out ./reports
"""

import argparse
import json
import os
from datetime import date, datetime

from fpdf import FPDF


# ---------------------------------------------------------------------
# 1. Load + derive the same numbers the dashboard shows
# ---------------------------------------------------------------------
def load_and_derive(data_path, budget):
    with open(data_path, "r") as f:
        raw = json.load(f)

    daily = raw.get("daily_costs", [])
    services = sorted(raw.get("by_service", []), key=lambda s: -s["amount"])
    anomalies = raw.get("anomalies", [])
    recommendations = raw.get("recommendations", [])

    spend_so_far = round(sum(d["amount"] for d in daily), 2)

    today = date.today()
    day_of_month = today.day
    # days in current month
    if today.month == 12:
        days_in_month = 31
    else:
        days_in_month = (date(today.year, today.month + 1, 1) - date(today.year, today.month, 1)).days

    projected = round((spend_so_far / max(day_of_month, 1)) * days_in_month, 2)
    over_budget = projected > budget
    over_percent = round(((projected - budget) / budget) * 100, 1) if over_budget else 0

    alerts = []
    for a in anomalies:
        z = a.get("z_score", 0)
        level = "Critical" if z > 3 else "Warning" if z > 2 else "Info"
        alerts.append({
            "title": f"Spend spike on {a['date']}",
            "level": level,
            "detail": f"Spent ${a['amount']} vs an expected ${a['expected']} (z-score {z}).",
            "impact": max(0, round(a["amount"] - a["expected"], 2)),
        })

    total_savings = round(sum(r.get("monthly_savings", 0) for r in recommendations), 2)
    annual_savings = round(total_savings * 12, 2)

    return {
        "spend_so_far": spend_so_far,
        "budget": budget,
        "projected": projected,
        "over_budget": over_budget,
        "over_percent": over_percent,
        "services": services,
        "alerts": alerts,
        "recommendations": recommendations,
        "total_savings": total_savings,
        "annual_savings": annual_savings,
    }


# ---------------------------------------------------------------------
# 2. Markdown report (easy to paste into an email/Notion doc)
# ---------------------------------------------------------------------
def build_markdown(client_name, your_name, d):
    lines = []
    lines.append(f"# Cloud Cost Report — {client_name}")
    lines.append(f"**Prepared by Xenkloud Pulse · {date.today().strftime('%B %d, %Y')}**\n")
    lines.append("---\n")
    lines.append("## Summary\n")
    lines.append(
        f"This month, {client_name} spent **${d['spend_so_far']}** against a budget of "
        f"**${d['budget']}**, currently pacing toward a projected month-end total of "
        f"**${d['projected']}**.\n"
    )
    if d["over_budget"]:
        lines.append(f"⚠️ At the current pace, this account is projected to run **{d['over_percent']}% over budget** this month.\n")
    else:
        lines.append("✅ At the current pace, this account is on track to stay within budget this month.\n")

    lines.append(
        f"We identified **{len(d['alerts'])} anomalies** and **${d['total_savings']}/month in available "
        f"savings** with low-to-medium effort to fix.\n"
    )
    lines.append("---\n\n## Where the money is going\n")
    lines.append("| Service | Monthly cost |\n|---|---|")
    for s in d["services"]:
        lines.append(f"| {s['name']} | ${s['amount']} |")

    lines.append("\n---\n\n## What looks unusual\n")
    if not d["alerts"]:
        lines.append("No anomalies detected this period.\n")
    for a in d["alerts"]:
        lines.append(f"**{a['title']}** — *{a['level']}*  \n{a['detail']}  \nEstimated impact: **+${a['impact']}/month**\n")

    lines.append("---\n\n## Recommended fixes, ranked by ease\n")
    lines.append("| # | Fix | Monthly savings | Effort |\n|---|---|---|---|")
    for i, r in enumerate(d["recommendations"], 1):
        lines.append(f"| {i} | {r['title']} | ${r.get('monthly_savings', 0)} | {r.get('effort', 'Medium')} |")

    lines.append(
        f"\n**Total available savings: ${d['total_savings']}/month** — roughly "
        f"**${d['annual_savings']}/year** if left unaddressed.\n"
    )
    lines.append("---\n\n## Next steps\n")
    lines.append(
        "1. Start with the \"Low effort\" items above — usually under an hour combined, no risk to production.\n"
        "2. Happy to implement these fixes directly if you'd prefer — just reply and let us know.\n"
        "3. Xenkloud Pulse keeps watching your account daily, so the next spike gets caught before the invoice.\n"
    )
    lines.append(f"\n*Questions about anything in this report? Reply directly.*\n\n**{your_name} · Xenkloud**")

    return "\n".join(lines)


# ---------------------------------------------------------------------
# 3. PDF report (clean, attachable)
# ---------------------------------------------------------------------
class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 20, 30)
        self.cell(0, 10, self.title, ln=True)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(120, 120, 130)
        self.cell(0, 6, f"Prepared by Xenkloud Pulse · {date.today().strftime('%B %d, %Y')}", ln=True)
        self.ln(4)
        self.set_draw_color(220, 220, 225)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def section_title(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 20, 30)
        self.ln(2)
        self.cell(0, 8, text, ln=True)
        self.set_text_color(60, 60, 70)
        self.set_font("Helvetica", "", 10)

    def body_text(self, text):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(40, 40, 50)
        self.multi_cell(0, 6, text)
        self.ln(1)


def build_pdf(client_name, your_name, d, out_path):
    pdf = ReportPDF()
    pdf.title = f"Cloud Cost Report — {client_name}"
    pdf.add_page()

    summary = (
        f"This month, {client_name} spent ${d['spend_so_far']} against a budget of ${d['budget']}, "
        f"pacing toward a projected month-end total of ${d['projected']}."
    )
    pdf.body_text(summary)

    if d["over_budget"]:
        pdf.set_text_color(200, 60, 60)
        pdf.body_text(f"Projected to run {d['over_percent']}% over budget this month.")
    else:
        pdf.set_text_color(40, 140, 110)
        pdf.body_text("On track to stay within budget this month.")

    pdf.set_text_color(40, 40, 50)
    pdf.body_text(
        f"Identified {len(d['alerts'])} anomalies and ${d['total_savings']}/month in available savings."
    )

    pdf.section_title("Where the money is going")
    for s in d["services"]:
        pdf.body_text(f"  {s['name']}: ${s['amount']}")

    pdf.section_title("What looks unusual")
    if not d["alerts"]:
        pdf.body_text("No anomalies detected this period.")
    for a in d["alerts"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, f"{a['title']} ({a['level']})", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, f"{a['detail']} Estimated impact: +${a['impact']}/month")
        pdf.ln(1)

    pdf.section_title("Recommended fixes, ranked by ease")
    for i, r in enumerate(d["recommendations"], 1):
        pdf.body_text(f"{i}. {r['title']} — ${r.get('monthly_savings', 0)}/mo · Effort: {r.get('effort', 'Medium')}")

    pdf.section_title("Total available savings")
    pdf.body_text(f"${d['total_savings']}/month  (~${d['annual_savings']}/year if left unaddressed)")

    pdf.section_title("Next steps")
    pdf.body_text(
        "1. Start with the Low effort items above.\n"
        "2. We're happy to implement these directly if preferred.\n"
        "3. Xenkloud Pulse keeps watching this account daily going forward."
    )

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 130)
    pdf.cell(0, 6, f"{your_name} - Xenkloud", ln=True)

    pdf.output(out_path)


# ---------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate a Xenkloud Pulse client report")
    parser.add_argument("--data", required=True, help="Path to the /api/summary JSON file")
    parser.add_argument("--client", required=True, help="Client name to show on the report")
    parser.add_argument("--budget", type=float, required=True, help="Client's monthly cloud budget")
    parser.add_argument("--your-name", default="Xenkloud Team", help="Your name for the sign-off")
    parser.add_argument("--out", default=".", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    derived = load_and_derive(args.data, args.budget)

    safe_client = args.client.replace(" ", "_").lower()
    date_str = datetime.now().strftime("%Y-%m-%d")

    md_path = os.path.join(args.out, f"{safe_client}_report_{date_str}.md")
    pdf_path = os.path.join(args.out, f"{safe_client}_report_{date_str}.pdf")

    with open(md_path, "w") as f:
        f.write(build_markdown(args.client, args.your_name, derived))

    build_pdf(args.client, args.your_name, derived, pdf_path)

    print(f"Markdown report: {md_path}")
    print(f"PDF report:      {pdf_path}")


if __name__ == "__main__":
    main()
