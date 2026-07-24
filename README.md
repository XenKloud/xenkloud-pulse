# Xenkloud Pulse

Cloud cost monitoring for indie and small SaaS founders — catch spend anomalies before the invoice does, and get plain-English fixes instead of a spreadsheet.

## Project structure

```
├── index.html              → Landing page (this is what GitHub Pages serves)
├── dashboard/
│   └── xenkloud-pulse.jsx  → React dashboard component (demo + "load real data" mode)
├── backend/
│   └── xenkloud_pulse_backend.py   → FastAPI service that pulls real AWS Cost Explorer data
├── tools/
│   └── xenkloud_pulse_report_generator.py  → Turns backend data into a client-ready PDF/Markdown report
└── docs/
    ├── xenkloud-pulse-client-setup-guide.md     → Send this to clients (AWS read-only key setup)
    └── xenkloud-pulse-client-report-template.md → Report format reference
```

## Status

- [x] Landing page
- [x] Dashboard demo (mock data + manual "paste real data" mode)
- [x] Backend scaffold (AWS Cost Explorer + anomaly detection + idle resource detection)
- [x] Report generator (Markdown + PDF)
- [ ] Live backend deployment
- [ ] Dashboard wired directly to backend (currently manual paste)
- [ ] Waitlist form connected to a real email capture

## Running the backend locally

```bash
cd backend
pip install boto3 fastapi uvicorn --break-system-packages
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
uvicorn xenkloud_pulse_backend:app --reload
```

## Generating a client report

```bash
cd tools
pip install fpdf2 --break-system-packages
python xenkloud_pulse_report_generator.py --data acme_data.json --client "Acme Inc" --budget 2800 --your-name "Your Name" --out ./reports
```
