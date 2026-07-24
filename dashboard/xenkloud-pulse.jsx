import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Zap,
  ChevronRight,
  Server,
  Database,
  HardDrive,
  Globe,
  Box,
  CheckCircle2,
} from "lucide-react";

const FONT_IMPORT = `@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');`;

// ---- Mock data (representative of a $500-5k/mo indie SaaS AWS bill) ----
const DAILY = [
  { d: "Jun 21", v: 61 }, { d: "Jun 22", v: 58 }, { d: "Jun 23", v: 64 },
  { d: "Jun 24", v: 60 }, { d: "Jun 25", v: 67 }, { d: "Jun 26", v: 63 },
  { d: "Jun 27", v: 69 }, { d: "Jun 28", v: 71 }, { d: "Jun 29", v: 66 },
  { d: "Jun 30", v: 70 }, { d: "Jul 1", v: 68 }, { d: "Jul 2", v: 72 },
  { d: "Jul 3", v: 75 }, { d: "Jul 4", v: 70 }, { d: "Jul 5", v: 74 },
  { d: "Jul 6", v: 78 }, { d: "Jul 7", v: 82 }, { d: "Jul 8", v: 79 },
  { d: "Jul 9", v: 118 }, { d: "Jul 10", v: 124 }, { d: "Jul 11", v: 96 },
  { d: "Jul 12", v: 88 }, { d: "Jul 13", v: 91 }, { d: "Jul 14", v: 95 },
  { d: "Jul 15", v: 98 }, { d: "Jul 16", v: 101 }, { d: "Jul 17", v: 97 },
  { d: "Jul 18", v: 103 }, { d: "Jul 19", v: 108 }, { d: "Jul 20", v: 112 },
];

const SERVICES = [
  { name: "EC2", value: 1180, icon: Server, delta: 4 },
  { name: "RDS (Postgres)", value: 640, icon: Database, delta: -2 },
  { name: "S3", value: 310, icon: Box, delta: 1 },
  { name: "EBS Volumes", value: 265, icon: HardDrive, delta: 38 },
  { name: "CloudFront", value: 190, icon: Globe, delta: 6 },
];

const ALERTS = [
  {
    id: 1,
    level: "critical",
    title: "EBS spend jumped 38% week-over-week",
    detail: "6 unattached volumes found in us-east-1, idle for 11+ days.",
    impact: 74,
  },
  {
    id: 2,
    level: "warning",
    title: "Daily spend spiked to $124 on Jul 10",
    detail: "Traced to a burst in EC2 on-demand hours — no matching deploy or traffic spike found.",
    impact: 46,
  },
  {
    id: 3,
    level: "info",
    title: "3 RDS snapshots older than 90 days",
    detail: "Retained snapshots with no restore activity — safe to review for deletion.",
    impact: 12,
  },
];

const RECS = [
  { title: "Delete 6 unattached EBS volumes", save: 74, effort: "Low" },
  { title: "Switch staging RDS to a smaller instance class", save: 58, effort: "Low" },
  { title: "Move cold S3 objects to Glacier Instant Retrieval", save: 31, effort: "Medium" },
  { title: "Right-size 2 oversized EC2 instances (avg CPU < 8%)", save: 112, effort: "Medium" },
];

const BUDGET = 2800;
const SPEND_SO_FAR = 1935;
const DAY_OF_MONTH = 20;
const DAYS_IN_MONTH = 31;
const PROJECTED = Math.round((SPEND_SO_FAR / DAY_OF_MONTH) * DAYS_IN_MONTH);

export default function XenkloudPulse() {
  const [range, setRange] = useState("30d");

  const timePct = Math.round((DAY_OF_MONTH / DAYS_IN_MONTH) * 100);
  const spendPct = Math.min(100, Math.round((SPEND_SO_FAR / BUDGET) * 100));
  const pacing = spendPct - timePct; // positive = spending ahead of schedule
  const pacingColor = pacing > 8 ? "var(--red)" : pacing > 0 ? "var(--amber)" : "var(--teal)";

  const totalSavings = useMemo(() => RECS.reduce((s, r) => s + r.save, 0), []);

  return (
    <div style={{ background: "var(--ink)", minHeight: "100vh", color: "var(--text-hi)", fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        ${FONT_IMPORT}
        :root {
          --ink: #0A0F1C;
          --panel: #111827;
          --panel-2: #16202F;
          --line: #232D42;
          --text-hi: #EDEFF5;
          --text-lo: #8996AC;
          --amber: #F0A83B;
          --teal: #34B8A1;
          --indigo: #6C7BFF;
          --red: #F0546B;
        }
        .mono { font-family: 'IBM Plex Mono', monospace; }
        .display { font-family: 'Space Grotesk', sans-serif; }
        .card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; }
        .track { background: var(--panel-2); border-radius: 999px; overflow: hidden; position: relative; }
        .fade-in { animation: fadeIn 0.5s ease-out both; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .row:hover { background: var(--panel-2); }
        ::selection { background: var(--indigo); color: white; }
      `}</style>

      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "28px 20px 80px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: "linear-gradient(135deg, var(--indigo), var(--teal))" }} />
            <div>
              <div className="display" style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.2 }}>Xenkloud Pulse</div>
              <div className="mono" style={{ fontSize: 11, color: "var(--text-lo)" }}>acme-app · AWS · us-east-1</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {["7d", "30d", "90d"].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 12,
                  padding: "6px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--line)",
                  background: range === r ? "var(--indigo)" : "transparent",
                  color: range === r ? "white" : "var(--text-lo)",
                  cursor: "pointer",
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {/* Hero: Burn tracker */}
        <div className="card fade-in" style={{ padding: 24, marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 12 }}>
            <div>
              <div style={{ fontSize: 13, color: "var(--text-lo)", marginBottom: 4 }}>Spent this month</div>
              <div className="mono" style={{ fontSize: 34, fontWeight: 600 }}>
                ${SPEND_SO_FAR.toLocaleString()}
                <span style={{ fontSize: 16, color: "var(--text-lo)", fontWeight: 400 }}> / ${BUDGET.toLocaleString()} budget</span>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 13, color: "var(--text-lo)", marginBottom: 4 }}>Projected month-end</div>
              <div className="mono" style={{ fontSize: 22, fontWeight: 600, color: PROJECTED > BUDGET ? "var(--red)" : "var(--teal)" }}>
                ${PROJECTED.toLocaleString()}
                {PROJECTED > BUDGET && <span style={{ fontSize: 13, marginLeft: 8 }}>+{Math.round(((PROJECTED - BUDGET) / BUDGET) * 100)}% over</span>}
              </div>
            </div>
          </div>

          {/* Pacing bar — the signature element: spend% vs time-elapsed% */}
          <div style={{ marginTop: 22 }}>
            <div className="track" style={{ height: 14, width: "100%" }}>
              <div style={{ position: "absolute", inset: 0, width: `${spendPct}%`, background: pacingColor, transition: "width 0.6s ease" }} />
              <div style={{ position: "absolute", top: -6, left: `${timePct}%`, width: 2, height: 26, background: "var(--text-hi)", opacity: 0.6 }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12, color: "var(--text-lo)" }}>
              <span>Day {DAY_OF_MONTH} of {DAYS_IN_MONTH} — {timePct}% of month elapsed</span>
              <span style={{ color: pacingColor, fontWeight: 600 }}>
                {pacing > 0 ? `Spending ${pacing}pts ahead of schedule` : `Spending ${Math.abs(pacing)}pts under schedule`}
              </span>
            </div>
          </div>
        </div>

        {/* Alerts */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <AlertTriangle size={16} color="var(--amber)" />
            <span className="display" style={{ fontWeight: 600, fontSize: 15 }}>Anomalies</span>
          </div>
          <div className="card">
            {ALERTS.map((a, i) => (
              <div
                key={a.id}
                className="row"
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "16px 20px", borderBottom: i < ALERTS.length - 1 ? "1px solid var(--line)" : "none",
                }}
              >
                <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: 999, marginTop: 6, flexShrink: 0,
                    background: a.level === "critical" ? "var(--red)" : a.level === "warning" ? "var(--amber)" : "var(--teal)",
                  }} />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{a.title}</div>
                    <div style={{ fontSize: 13, color: "var(--text-lo)", marginTop: 2 }}>{a.detail}</div>
                  </div>
                </div>
                <div className="mono" style={{ fontSize: 14, color: "var(--red)", whiteSpace: "nowrap", marginLeft: 12 }}>
                  +${a.impact}/mo
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Two column: trend + breakdown */}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, marginBottom: 20 }}>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <span className="display" style={{ fontWeight: 600, fontSize: 15 }}>Daily spend</span>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-lo)" }}>last 30 days</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={DAILY}>
                <defs>
                  <linearGradient id="spend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6C7BFF" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#6C7BFF" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#232D42" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="d" tick={{ fill: "#8996AC", fontSize: 10 }} interval={4} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#8996AC", fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
                <Tooltip
                  contentStyle={{ background: "#16202F", border: "1px solid #232D42", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#8996AC" }}
                  formatter={(v) => [`$${v}`, "Spend"]}
                />
                <Area type="monotone" dataKey="v" stroke="#6C7BFF" strokeWidth={2} fill="url(#spend)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ padding: 20 }}>
            <div className="display" style={{ fontWeight: 600, fontSize: 15, marginBottom: 14 }}>By service</div>
            {SERVICES.sort((a, b) => b.value - a.value).map((s) => {
              const Icon = s.icon;
              const max = Math.max(...SERVICES.map((x) => x.value));
              return (
                <div key={s.name} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 5 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-hi)" }}>
                      <Icon size={13} color="var(--text-lo)" /> {s.name}
                    </span>
                    <span className="mono" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      ${s.value}
                      {s.delta !== 0 && (
                        <span style={{ fontSize: 11, color: s.delta > 15 ? "var(--red)" : s.delta > 0 ? "var(--amber)" : "var(--teal)", display: "flex", alignItems: "center" }}>
                          {s.delta > 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                          {Math.abs(s.delta)}%
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="track" style={{ height: 6 }}>
                    <div style={{ width: `${(s.value / max) * 100}%`, height: "100%", background: "var(--indigo)", opacity: 0.85 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recommendations */}
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Zap size={16} color="var(--teal)" />
              <span className="display" style={{ fontWeight: 600, fontSize: 15 }}>Recommendations</span>
            </div>
            <span className="mono" style={{ fontSize: 13, color: "var(--teal)" }}>${totalSavings}/mo available</span>
          </div>
          <div className="card">
            {RECS.map((r, i) => (
              <div
                key={r.title}
                className="row"
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "15px 20px", borderBottom: i < RECS.length - 1 ? "1px solid var(--line)" : "none", cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <CheckCircle2 size={16} color="var(--text-lo)" />
                  <div>
                    <div style={{ fontSize: 14 }}>{r.title}</div>
                    <div style={{ fontSize: 12, color: "var(--text-lo)", marginTop: 2 }}>Effort: {r.effort}</div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="mono" style={{ color: "var(--teal)", fontSize: 14 }}>+${r.save}/mo</span>
                  <ChevronRight size={15} color="var(--text-lo)" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
