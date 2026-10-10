"""Pure calculations for KeepMore. No Streamlit or network dependencies."""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from statistics import median
import calendar
import hashlib
import io
import re
import pandas as pd

CATEGORIES = ["Housing", "Groceries", "Dining", "Transport", "Utilities", "Insurance", "Health", "Shopping", "Entertainment", "Subscriptions", "Education", "Family", "Other"]
COLORS = {"Housing":"#326a7f","Groceries":"#3aa18f","Dining":"#f4a96a","Transport":"#6985d6","Utilities":"#bb8bcf","Insurance":"#73b5db","Health":"#e6889f","Shopping":"#e1bd68","Entertainment":"#8c83d6","Subscriptions":"#4cafa6","Education":"#b0b963","Family":"#d48eb8","Other":"#8e9ba2"}
CYCLES = {"Weekly":52, "Biweekly":26, "Monthly":12, "Quarterly":4, "Yearly":1}
KEYWORDS = {
    "Housing": ["rent", "mortgage", "property manager", "leasing"],
    "Groceries": ["grocery", "market", "whole foods", "kroger", "aldi", "trader joe", "costco", "supermarket", "publix"],
    "Dining": ["restaurant", "coffee", "cafe", "pizza", "dining", "takeout", "doordash", "chipotle", "starbucks"],
    "Transport": ["gas station", "fuel", "uber", "lyft", "shell", "chevron", "metro", "parking", "transit", "car wash"],
    "Utilities": ["electric", "power", "water", "internet", "broadband", "mobile", "wireless", "cellular", "utility", "phone bill"],
    "Insurance": ["insurance", "geico", "progressive", "state farm"],
    "Health": ["pharmacy", "medical", "doctor", "hospital", "dental", "clinic"],
    "Entertainment": ["cinema", "theater", "movie", "ticket", "concert", "game"],
    "Subscriptions": ["netflix", "spotify", "hulu", "stream", "musicflow", "cloudbox", "fitclub", "designpro", "subscription", "membership"],
    "Education": ["tuition", "school", "university", "textbook", "college"],
    "Family": ["daycare", "childcare", "kid", "pet care"],
    "Shopping": ["amazon", "target", "walmart", "shop", "store", "retail", "clothing"],
}

def cents(value) -> int:
    """Money string to signed cents. Reject ambiguous/bad numeric content."""
    if isinstance(value, (int, float, Decimal)):
        value = str(value)
    s = str(value or "").strip()
    if not s:
        raise ValueError("Missing amount")
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("$", "").replace(",", "").replace(" ", "").replace("(", "").replace(")", "")
    try:
        d = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount: {value}") from exc
    if not d.is_finite():
        raise ValueError("Invalid amount")
    if negative:
        d = -abs(d)
    if abs(d) > Decimal("1000000000"):
        raise ValueError("Amount is out of supported range")
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def money(value: int | float) -> str:
    neg = "−" if value < 0 else ""
    return f"{neg}${abs(value)/100:,.2f}"

def normalize_merchant(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"\b(?:pos|debit|credit|recurring|payment|purchase|online|ach|card|visa|mc|inc|llc|co)\b", " ", value)
    value = re.sub(r"\b\d{3,}\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())[:100] or "unknown"

def classify_merchant(description: str) -> str:
    d = (description or "").lower()
    for category, terms in KEYWORDS.items():
        if any(t in d for t in terms):
            return category
    return "Other"

def add_months(d: date, months: int, anchor_day: int | None = None) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    m += 1
    return date(y, m, min(anchor_day or d.day, calendar.monthrange(y, m)[1]))

def next_due(on: date, cycle: str, today: date | None = None) -> date:
    """Move a due date forward without retroactively changing original anchor."""
    today = today or date.today()
    current = on
    if current >= today:
        return current
    if cycle in ("Weekly", "Biweekly"):
        days = 7 if cycle == "Weekly" else 14
        steps = (today - on).days // days
        current = on + timedelta(days=steps * days)
        if current < today:
            current += timedelta(days=days)
        return current
    months = {"Monthly":1,"Quarterly":3,"Yearly":12}.get(cycle, 1)
    steps = max(0, ((today.year-on.year)*12 + today.month-on.month)//months)
    current = add_months(on, steps * months, on.day)
    while current < today:
        steps += 1
        current = add_months(on, steps * months, on.day)
    return current

def monthly_equivalent(amount_cents: int, cycle: str) -> float:
    return amount_cents * CYCLES.get(cycle, 12) / 12

def monthly_totals(rows: list[dict]) -> list[dict]:
    agg = defaultdict(lambda:{"spend":0,"income":0})
    for r in rows:
        ym = str(r["occurred_on"])[:7]
        amount = int(r["amount_cents"])
        if amount < 0:
            agg[ym]["spend"] += abs(amount)
        else:
            agg[ym]["income"] += amount
    return [{"month":k,"spend":v["spend"],"income":v["income"]} for k,v in sorted(agg.items())]

def category_spend(rows: list[dict], month: str | None = None) -> dict[str, int]:
    totals: dict[str,int] = defaultdict(int)
    for r in rows:
        if int(r["amount_cents"]) < 0 and (month is None or str(r["occurred_on"])[:7] == month):
            totals[r.get("category") or "Other"] += abs(int(r["amount_cents"]))
    return dict(sorted(totals.items(), key=lambda x:-x[1]))

def detect_recurring(rows: list[dict], existing: list[dict] | None = None, today: date | None = None) -> list[dict]:
    """Reviewable recurring candidates from multiple distinct payments. Never creates subscriptions automatically."""
    today = today or date.today()
    known = {normalize_merchant(x["merchant"]) for x in (existing or []) if x.get("status") != "cancelled"}
    groups = defaultdict(list)
    for r in rows:
        if int(r["amount_cents"]) < 0:
            key = normalize_merchant(r["merchant"])
            if key not in known:
                groups[key].append(r)
    out=[]
    for key, items in groups.items():
        by_day={}
        for r in items:
            on=date.fromisoformat(str(r["occurred_on"])[:10])
            by_day.setdefault(on,[]).append(r)
        dates=sorted(by_day)
        if len(dates)<3:
            continue
        diffs=[(b-a).days for a,b in zip(dates,dates[1:])]
        gap=float(median(diffs))
        if 6<=gap<=8:
            cycle="Weekly"
        elif 12<=gap<=16:
            cycle="Biweekly"
        elif 25<=gap<=36:
            cycle="Monthly"
        elif 80<=gap<=101:
            cycle="Quarterly"
        elif 345<=gap<=385:
            cycle="Yearly"
        else:
            continue
        near=sum(abs(d-gap)<=max(3, gap*0.22) for d in diffs)
        if near < len(diffs) * .75:
            continue
        paid=[abs(int(r["amount_cents"])) for r in sorted(items,key=lambda r:r["occurred_on"])]
        typical=int(median(paid[-3:]))
        if typical < 100 or not paid:
            continue
        ratio=max(paid)/max(1,min(paid))
        if ratio>2.3:  # Reject irregular discretionary spend.
            continue
        last=dates[-1]
        if (today-last).days > max(60, gap*2.4):
            continue
        representative=max(items, key=lambda r:r["occurred_on"])
        if cycle in ("Weekly", "Biweekly"):
            following=last+timedelta(days=7 if cycle=="Weekly" else 14)
        else:
            following=add_months(last,{"Monthly":1,"Quarterly":3,"Yearly":12}[cycle])
        planned=next_due(following,cycle,today)
        out.append({"merchant":representative["merchant"],"category":representative.get("category") or classify_merchant(key),"amount_cents":typical,"cycle":cycle,"next_due":planned.isoformat(),"payments":len(dates),"confidence":"High" if len(dates)>=4 and ratio<1.2 else "Review", "key":key})
    return sorted(out,key=lambda r:(r["confidence"]!="High",-monthly_equivalent(r["amount_cents"],r["cycle"])))

def detect_price_increase(merchant: str, rows: list[dict], current_cents: int) -> dict | None:
    key=normalize_merchant(merchant)
    values=[abs(int(r["amount_cents"])) for r in sorted(rows,key=lambda x:x["occurred_on"]) if int(r["amount_cents"])<0 and normalize_merchant(r["merchant"])==key]
    if len(values)<3:
        return None
    old=median(values[:-1])
    latest=values[-1]
    if old > 0 and latest-old>=200 and (latest/old-1)>=0.08 and abs(current_cents-latest)<=max(200,latest*.2):
        return {"old_cents":int(old),"new_cents":latest,"increase_cents":int(latest-old),"increase_pct":round((latest/old-1)*100,1)}
    return None

def opportunities(recurring: list[dict], transactions: list[dict]) -> list[dict]:
    items=[]
    for sub in recurring:
        if sub["status"] != "active":
            continue
        normalized=normalize_merchant(sub["merchant"])
        monthly=monthly_equivalent(int(sub["amount_cents"]),sub["cycle"])
        if sub.get("usage") == "Not using":
            items.append({"key":f"unused-{sub['id']}","kind":"Cancel or pause","title":f"Review {sub['merchant']}","reason":"You marked this service as not in use. Review its cancellation terms before taking action.","annual_cents":round(monthly*12),"recurring_id":sub["id"],"merchant":sub["merchant"],"priority":1,"evidence":"Your usage rating"})
        increase=detect_price_increase(sub["merchant"],transactions,int(sub["amount_cents"]))
        if increase:
            # Exclude duplicate savings figures from a not-used item.
            items.append({"key":f"increase-{sub['id']}","kind":"Price change","title":f"Price increase: {sub['merchant']}","reason":f"Latest observed payment {money(increase['new_cents'])}, earlier median {money(increase['old_cents'])}. Ask about restoring your previous rate.","annual_cents":0 if sub.get("usage")=="Not using" else round(increase["increase_cents"]*CYCLES.get(sub["cycle"],12)),"recurring_id":sub["id"],"merchant":sub["merchant"],"priority":2,"evidence":"Your recorded transactions"})
        if monthly>=7500 and sub.get("usage") != "Not using" and not increase:
            items.append({"key":f"review-{sub['id']}","kind":"Rate review","title":f"Review your {sub['merchant']} bill","reason":f"This recurring commitment is {money(round(monthly))} per month. Compare current plan terms or request a loyalty offer.","annual_cents":0,"recurring_id":sub["id"],"merchant":sub["merchant"],"priority":3,"evidence":"Your recurring plan"})
    return sorted(items,key=lambda o:(o["priority"],-o["annual_cents"]))

def script_for(merchant: str, amount_cents: int, kind: str, old_cents: int | None = None) -> str:
    amount=money(amount_cents)
    if kind=="Cancel or pause":
        return f"Hello, I'd like to cancel or pause my {merchant} subscription before its next renewal. Please confirm the effective date, any remaining charges, and whether the cancellation is complete. Please send written confirmation to my account email. Thank you."
    if kind=="Price change":
        detail = f" My previous bill was around {money(old_cents)}." if old_cents else ""
        return f"Hello, I am reviewing my household expenses. My current {merchant} charge is {amount}.{detail} Are there any current promotions, loyalty rates, or lower-cost plans with comparable service? Please tell me the total price, fees, term, and whether switching affects my existing benefits. Thank you."
    return f"Hello, I'm reviewing my household costs. I currently pay {amount} to {merchant}. Can you review my plan for any loyalty discounts, comparable lower-cost options, or fees I no longer need? Please confirm the total monthly price and any contract changes before making changes. Thank you."

def calendar_ics(recurring: list[dict]) -> bytes:
    def esc(s: str) -> str:
        return str(s).replace("\\","\\\\").replace("\n","\\n").replace(",","\\,").replace(";","\\;")
    lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//KeepMore//Bills//EN","CALSCALE:GREGORIAN"]
    today=date.today()
    for r in recurring:
        if r["status"] != "active":
            continue
        due=next_due(date.fromisoformat(r["next_due"]),r["cycle"],today)
        uid=hashlib.sha256(f"{r['id']}-{r['merchant']}-{due.isoformat()}".encode()).hexdigest()[:20]
        lines.extend(["BEGIN:VEVENT",f"UID:{uid}@keepmore.local",f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",f"SUMMARY:{esc('Bill due: '+r['merchant'])}",f"DESCRIPTION:{esc('Expected charge '+money(r['amount_cents'])+'; verify with your provider.')}", "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return ("\r\n".join(x.strip("\n") for x in lines)+"\r\n").encode("utf-8")

def parse_csv(upload: bytes, mapping: dict, sign_mode: str = "negative", dayfirst: bool = False) -> tuple[list[dict],list[str]]:
    """CSV parser with explicit user-approved columns and signs. Expense amounts are negative."""
    df=pd.read_csv(io.BytesIO(upload), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if len(df)>50_000:
        raise ValueError("Import a maximum of 50,000 rows at once")
    result=[]; errors=[]
    for ix,r in df.iterrows():
        try:
            raw_date=str(r[mapping["date"]]).strip()
            parsed=pd.to_datetime(raw_date,dayfirst=dayfirst,errors="raise")
            on=parsed.date()
            if on>date.today()+timedelta(days=3):
                raise ValueError("Date lies in the future")
            merchant=str(r[mapping["description"]]).strip()
            if not merchant:
                raise ValueError("Missing merchant")
            if mapping.get("debit") and mapping.get("credit"):
                debit=cents(r[mapping["debit"]]) if str(r[mapping["debit"]]).strip() else 0
                credit=cents(r[mapping["credit"]]) if str(r[mapping["credit"]]).strip() else 0
                if debit and credit:
                    raise ValueError("Debit and credit are both populated")
                amount=abs(credit)-abs(debit)
            else:
                amount=cents(r[mapping["amount"]])
                if sign_mode=="positive":
                    amount=-amount
            if not amount:
                continue
            cat=str(r[mapping["category"]]).strip() if mapping.get("category") else ""
            if cat not in CATEGORIES:
                cat=classify_merchant(merchant)
            result.append({"occurred_on":on.isoformat(),"merchant":merchant[:160],"amount_cents":amount,"category":cat,"note":"CSV import"})
        except Exception as exc:
            errors.append(f"Row {ix+2}: {str(exc)[:105]}")
    return result,errors
