"""
Xenkloud Pulse — report generator

Takes the raw JSON from xenkloud_pulse_backend.py's /api/summary endpoint
and turns it into a client-ready report: a Markdown file (easy to paste
into an email) and a polished PDF (easy to attach/send).

Setup:
    pip install reportlab matplotlib --break-system-packages

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
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def email_report(client_email, client_name, pdf_path, smtp_config):
    """Emails the generated PDF report directly to the client — closes the
    loop so delivery doesn't depend on you remembering to hit send manually.
    smtp_config = {"host", "port", "user", "password", "from_addr"}"""
    msg = MIMEMultipart()
    msg["Subject"] = f"Your Xenkloud Pulse report — {date.today().strftime('%B %Y')}"
    msg["From"] = f"Xenkloud Pulse <{smtp_config['from_addr']}>"
    msg["To"] = client_email

    body = (
        f"Hi {client_name},\n\n"
        f"Your latest Xenkloud Pulse cost report is attached.\n\n"
        f"Questions about anything in it? Just reply to this email.\n\n"
        f"Got 2 minutes? We'd genuinely value your honest feedback so far: "
        f"https://pulse.xenkloud.com/feedback.html\n\n"
        f"— Xenkloud Team"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
    msg.attach(part)

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=10) as server:
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.sendmail(smtp_config["from_addr"], [client_email], msg.as_string())


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
        "daily": daily,
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
# 3. Charts (matplotlib) — the "pictures" half of the report
# ---------------------------------------------------------------------
def _style_axes(ax):
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#D8DCE3")
    ax.tick_params(colors="#5B5F6B", labelsize=8)
    ax.grid(axis="y", color="#ECEDF1", linewidth=0.8)
    ax.set_axisbelow(True)


def generate_trend_chart(daily, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime as dt

    dates = [dt.strptime(d["date"], "%Y-%m-%d") for d in daily]
    amounts = [d["amount"] for d in daily]

    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=200)
    ax.plot(dates, amounts, color="#3B82F6", linewidth=2)
    ax.fill_between(dates, amounts, color="#3B82F6", alpha=0.12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 6)))
    ax.set_ylabel("USD/day", fontsize=8, color="#5B5F6B")
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(out_path, transparent=True)
    plt.close(fig)


def generate_service_chart(services, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = services[:6][::-1]  # reversed so largest is on top in a horizontal bar chart
    names = [s["name"].replace("Amazon ", "").replace("Elastic Compute Cloud - Compute", "EC2") for s in top]
    values = [s["amount"] for s in top]

    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    bars = ax.barh(names, values, color="#DD7A33", height=0.55)
    ax.set_xlabel("USD this month", fontsize=8, color="#5B5F6B")
    _style_axes(ax)
    ax.grid(axis="x", color="#ECEDF1", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                 f"${val:,.0f}", va="center", fontsize=8, color="#14161B")
    fig.tight_layout()
    fig.savefig(out_path, transparent=True)
    plt.close(fig)


# ---------------------------------------------------------------------
# 4. PDF report — branded header, charts, and clean typography
# ---------------------------------------------------------------------
INK = "#14161B"
GRAY = "#5B5F6B"
LINE = "#ECEDF1"
ORANGE = "#DD7A33"
TEAL = "#0F6E56"
RED = "#C83C3C"
PAGE_W, PAGE_H = letter
MARGIN = 42


def build_pdf(client_name, your_name, d, out_path):
    import tempfile

    c = canvas.Canvas(out_path, pagesize=letter)

    def header(title_text):
        c.setFillColor(INK)
        c.rect(0, PAGE_H - 58, PAGE_W, 58, fill=1, stroke=0)
        c.setFillColor("#FFFFFF")
        c.setFont("Helvetica-Bold", 15)
        c.drawString(MARGIN, PAGE_H - 26, "XENKLOUD PULSE")
        c.setFont("Helvetica", 9)
        c.setFillColor("#DCDCE1")
        c.drawString(MARGIN, PAGE_H - 40, "Cloud cost report")

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(MARGIN, PAGE_H - 84, title_text)
        c.setFont("Helvetica", 10)
        c.setFillColor(GRAY)
        c.drawString(MARGIN, PAGE_H - 100, f"Prepared {date.today().strftime('%B %d, %Y')}")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.75)
        c.line(MARGIN, PAGE_H - 110, PAGE_W - MARGIN, PAGE_H - 110)
        return PAGE_H - 130

    def footer(page_num):
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(GRAY)
        c.drawCentredString(PAGE_W / 2, 24, f"Xenkloud Pulse  |  Page {page_num}")

    def section_title(y, text):
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(MARGIN, y, text)
        c.setStrokeColor(ORANGE)
        c.setLineWidth(2.2)
        c.line(MARGIN, y - 5, MARGIN + 26, y - 5)
        return y - 26

    def stat_card(x, y, w, h, label, value, color):
        c.setFillColor("#FAFAFB")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.75)
        c.roundRect(x, y - h, w, h, 6, fill=1, stroke=1)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 12, y - 18, label)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 12, y - 36, value)

    page_num = 1
    y = header(client_name)
    footer(page_num)

    card_w = (PAGE_W - 2 * MARGIN - 2 * 12) / 3
    card_h = 48
    projected_color = RED if d["over_budget"] else TEAL
    stat_card(MARGIN, y, card_w, card_h, "SPENT THIS MONTH", f"${d['spend_so_far']:,.0f}", INK)
    stat_card(MARGIN + card_w + 12, y, card_w, card_h, "PROJECTED TOTAL", f"${d['projected']:,.0f}", projected_color)
    stat_card(MARGIN + 2 * (card_w + 12), y, card_w, card_h, "AVAILABLE SAVINGS", f"${d['total_savings']:,.0f}/mo", TEAL)
    y -= card_h + 20

    c.setFillColor("#28292E")
    c.setFont("Helvetica", 10.5)
    summary = (
        f"{client_name} spent ${d['spend_so_far']:,.2f} against a budget of ${d['budget']:,.2f} this month, "
        f"pacing toward a projected total of ${d['projected']:,.2f}."
    )
    c.drawString(MARGIN, y, summary[:100])
    y -= 16
    c.setFillColor(RED if d["over_budget"] else TEAL)
    status_line = (
        f"Projected to run {d['over_percent']}% over budget this month."
        if d["over_budget"] else "On track to stay within budget this month."
    )
    c.drawString(MARGIN, y, status_line)
    y -= 28

    with tempfile.TemporaryDirectory() as tmpdir:
        trend_path = os.path.join(tmpdir, "trend.png")
        service_path = os.path.join(tmpdir, "services.png")
        generate_trend_chart(d["daily"], trend_path)
        generate_service_chart(d["services"], service_path)

        y = section_title(y, "Daily spend, last 30 days")
        img = ImageReader(trend_path)
        iw, ih = img.getSize()
        draw_w = PAGE_W - 2 * MARGIN
        draw_h = draw_w * ih / iw
        c.drawImage(img, MARGIN, y - draw_h, width=draw_w, height=draw_h, mask="auto")
        y -= draw_h + 24

        if y < 260:
            footer(page_num)
            c.showPage()
            page_num += 1
            y = header(client_name)

        y = section_title(y, "Where the money is going")
        img2 = ImageReader(service_path)
        iw2, ih2 = img2.getSize()
        draw_h2 = draw_w * ih2 / iw2
        c.drawImage(img2, MARGIN, y - draw_h2, width=draw_w, height=draw_h2, mask="auto")
        y -= draw_h2 + 20

    if y < 220:
        footer(page_num)
        c.showPage()
        page_num += 1
        y = header(client_name)

    y = section_title(y, "What looks unusual")
    if not d["alerts"]:
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN, y, "No anomalies detected this period.")
        y -= 18
    for a in d["alerts"]:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(MARGIN, y, f"{a['title']}  ({a['level']})")
        y -= 14
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawString(MARGIN, y, f"{a['detail']} Estimated impact: +${a['impact']}/month"[:110])
        y -= 20

    if y < 220:
        footer(page_num)
        c.showPage()
        page_num += 1
        y = header(client_name)

    y = section_title(y, "Recommended fixes, ranked by ease")
    col_x = [MARGIN, MARGIN + 26, MARGIN + 300, MARGIN + 370]
    headers = ["#", "Fix", "Savings", "Effort"]
    c.setFillColor(INK)
    c.rect(MARGIN, y - 20, PAGE_W - 2 * MARGIN, 20, fill=1, stroke=0)
    c.setFillColor("#FFFFFF")
    c.setFont("Helvetica-Bold", 9.5)
    for x, htext in zip(col_x, headers):
        c.drawString(x + 4, y - 14, htext)
    y -= 20

    for i, r in enumerate(d["recommendations"], 1):
        row_h = 22
        if i % 2 == 0:
            c.setFillColor("#FAFAFB")
            c.rect(MARGIN, y - row_h, PAGE_W - 2 * MARGIN, row_h, fill=1, stroke=0)
        c.setFillColor("#28292E")
        c.setFont("Helvetica", 9.5)
        c.drawString(col_x[0] + 4, y - 15, str(i))
        c.drawString(col_x[1] + 4, y - 15, r["title"][:48])
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(col_x[2] + 4, y - 15, f"${r.get('monthly_savings', 0):,.0f}/mo")
        c.setFillColor("#28292E")
        c.setFont("Helvetica", 9.5)
        c.drawString(col_x[3] + 4, y - 15, r.get("effort", "Medium"))
        y -= row_h

    y -= 16
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, y, f"Total available savings: ${d['total_savings']:,.0f}/month  (~${d['annual_savings']:,.0f}/year)")
    y -= 24
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(MARGIN, y, f"{your_name} · Xenkloud  ·  Questions? Reply to this email.")

    footer(page_num)
    c.save()


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
    parser.add_argument("--email-to", help="Client's email — if set, automatically emails the PDF")
    parser.add_argument("--smtp-host", default=os.environ.get("SMTP_HOST", "smtp.ionos.com"))
    parser.add_argument("--smtp-port", type=int, default=int(os.environ.get("SMTP_PORT", "587")))
    parser.add_argument("--smtp-user", default=os.environ.get("SMTP_USER", "hello@xenkloud.com"))
    parser.add_argument("--smtp-password", default=os.environ.get("SMTP_PASSWORD", ""))
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

    if args.email_to:
        if not args.smtp_password:
            print("SMTP_PASSWORD not set — skipping email, PDF still saved locally.")
        else:
            email_report(
                client_email=args.email_to,
                client_name=args.client,
                pdf_path=pdf_path,
                smtp_config={
                    "host": args.smtp_host,
                    "port": args.smtp_port,
                    "user": args.smtp_user,
                    "password": args.smtp_password,
                    "from_addr": args.smtp_user,
                },
            )
            print(f"Emailed report to: {args.email_to}")


if __name__ == "__main__":
    main()
