"""
Xenkloud Pulse — backend scaffold
Fetches real AWS cost data, detects anomalies, and generates savings
recommendations. This is a starting point to wire up to the dashboard
(xenkloud-pulse.jsx) once you have real client AWS accounts connected.

Setup:
    pip install boto3 fastapi uvicorn --break-system-packages

Auth:
    Assumes a read-only IAM role/user with:
      - ce:GetCostAndUsage
      - ec2:DescribeVolumes, ec2:DescribeInstances
      - cloudwatch:GetMetricStatistics
    Credentials picked up via standard AWS credential chain
    (env vars, ~/.aws/credentials, or an assumed role per client account).

Run:
    uvicorn xenkloud_pulse_backend:app --reload
"""

from datetime import date, timedelta
from statistics import mean, stdev
from fastapi import FastAPI
import boto3

app = FastAPI(title="Xenkloud Pulse API")

ce = boto3.client("ce")          # Cost Explorer
ec2 = boto3.client("ec2")        # EC2 / EBS


# ---------------------------------------------------------------------
# 1. Cost data
# ---------------------------------------------------------------------
def get_daily_costs(days: int = 30):
    """Returns a list of {date, amount} for the last `days` days."""
    end = date.today()
    start = end - timedelta(days=days)

    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
    )

    return [
        {
            "date": r["TimePeriod"]["Start"],
            "amount": round(float(r["Total"]["UnblendedCost"]["Amount"]), 2),
        }
        for r in resp["ResultsByTime"]
    ]


def get_cost_by_service(days: int = 30):
    """Returns spend grouped by AWS service for the last `days` days."""
    end = date.today()
    start = end - timedelta(days=days)

    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    services = []
    for group in resp["ResultsByTime"][0]["Groups"]:
        amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
        if amount > 0.5:  # filter noise
            services.append({"name": group["Keys"][0], "amount": round(amount, 2)})

    return sorted(services, key=lambda s: -s["amount"])


# ---------------------------------------------------------------------
# 2. Anomaly detection (simple z-score on daily spend)
# ---------------------------------------------------------------------
def detect_anomalies(daily_costs, z_threshold: float = 2.0):
    amounts = [d["amount"] for d in daily_costs]
    if len(amounts) < 7:
        return []

    baseline = amounts[:-1]  # all but the most recent day(s)
    m, s = mean(baseline), stdev(baseline) if len(baseline) > 1 else 1

    anomalies = []
    for d in daily_costs:
        if s == 0:
            continue
        z = (d["amount"] - m) / s
        if z > z_threshold:
            anomalies.append({
                "date": d["date"],
                "amount": d["amount"],
                "expected": round(m, 2),
                "z_score": round(z, 2),
            })
    return anomalies


# ---------------------------------------------------------------------
# 3. Idle resource detection (unattached EBS volumes)
# ---------------------------------------------------------------------
def find_idle_ebs_volumes():
    resp = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
    volumes = []
    for v in resp["Volumes"]:
        # "available" status = not attached to any instance = pure waste
        monthly_estimate = v["Size"] * 0.10  # ~$0.10/GB-month for gp3, adjust per region
        volumes.append({
            "volume_id": v["VolumeId"],
            "size_gb": v["Size"],
            "created": v["CreateTime"].isoformat(),
            "estimated_monthly_cost": round(monthly_estimate, 2),
        })
    return volumes


# ---------------------------------------------------------------------
# 4. API endpoints
# ---------------------------------------------------------------------
@app.get("/api/costs/daily")
def daily_costs(days: int = 30):
    return get_daily_costs(days)


@app.get("/api/costs/by-service")
def by_service(days: int = 30):
    return get_cost_by_service(days)


@app.get("/api/anomalies")
def anomalies(days: int = 30):
    daily = get_daily_costs(days)
    return detect_anomalies(daily)


@app.get("/api/recommendations")
def recommendations():
    idle_volumes = find_idle_ebs_volumes()
    total_savings = sum(v["estimated_monthly_cost"] for v in idle_volumes)

    recs = []
    if idle_volumes:
        recs.append({
            "title": f"Delete {len(idle_volumes)} unattached EBS volume(s)",
            "monthly_savings": round(total_savings, 2),
            "effort": "Low",
            "detail": idle_volumes,
        })

    return recs


@app.get("/api/summary")
def summary():
    """Single call the dashboard can use to populate the whole view."""
    daily = get_daily_costs(30)
    return {
        "daily_costs": daily,
        "by_service": get_cost_by_service(30),
        "anomalies": detect_anomalies(daily),
        "recommendations": recommendations(),
    }
