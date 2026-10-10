"""KeepMore | Privacy-first household savings navigator. Run: streamlit run app.py"""
from __future__ import annotations
import csv
import html
import io
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pypdf import PdfReader

from keepmore.demo import seed
from keepmore.engine import (CATEGORIES, CYCLES, COLORS, add_months, calendar_ics,
    category_spend, cents, classify_merchant, detect_price_increase, detect_recurring,
    money, monthly_equivalent, monthly_totals, next_due, opportunities, parse_csv, script_for)
from keepmore.store import (actions_savings, add_goal, add_recurring, add_transaction,
    clear_workspace, db, export_database, get_setting, path_for, rows, setting)

st.set_page_config(page_title="KeepMore | Make room for more", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
ROOT=Path(__file__).parent
TODAY=date.today()
DATA_DIR=os.getenv("KEEPMORE_DATA_DIR",str(ROOT/"data"))
NAV=["Overview","Money moves","Recurring","Transactions","Bills & renewals","Budget studio","Goals & decisions","Ask KeepMore","Settings"]

def h(value): return html.escape(str(value),quote=True)

def style():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {--ink:#142D36; --mute:#637981;--mint:#0F9D82;--light:#f6f9f9;--line:#e5ecee;--nav:#0B2A35;}
    html,body,[class*=css], [data-testid="stApp"] {font-family:'DM Sans','Segoe UI',sans-serif;}
    [data-testid="stAppViewContainer"] {background:#F7F9FA;}
    [data-testid="stMainBlockContainer"] {padding-top:1.5rem; padding-bottom:3.5rem; max-width:1440px;}
    h1,h2,h3,h4 {font-family:'Manrope','DM Sans',sans-serif !important;letter-spacing:-.035em;color:#17323C;}
    h1 {font-size:2.2rem !important; font-weight:800 !important;}
    h2 {font-size:1.45rem !important; font-weight:800 !important;}
    h3 {font-size:1.05rem !important; font-weight:800 !important;}
    /* Limit page copy styling to content, never native controls. */
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] > p {color:#506771;}
    [data-testid="stSidebar"] {background:linear-gradient(170deg,#0C2C37 0%,#123D45 72%,#185448 100%) !important;}
    /* Keep sidebar copy readable without changing segmented-control labels. */
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] > p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {color:#e7f4f0;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label {padding:8px 10px;border-radius:11px;transition:background .15s;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:rgba(255,255,255,.09);}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:rgba(29,181,146,.20);}
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {font-size:.94rem;font-weight:600;}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {gap:2px;}
    [data-testid="stSidebar"] [data-testid="stRadio"] div[data-testid="stWidgetLabel"] {display:none;}
    [data-testid="stSidebar"] hr {border-color:#31535B;}
    .brandline {display:flex;align-items:center;gap:13px; padding:18px 0 12px;}
    .brandmark {width:41px;height:41px;background:linear-gradient(145deg,#5de2bd,#22b698);border-radius:14px;display:flex;align-items:center;justify-content:center;color:#083a36;font-size:28px;font-weight:800;box-shadow:0 8px 28px #06211d44;}
    .brandtitle {font-weight:800;letter-spacing:-.07em;font-size:25px;color:#fff;line-height:1.1;}
    .brandsub {font-size:10px;letter-spacing:.16em;color:#aed8cb;text-transform:uppercase;margin-top:4px;}
    .sidebar-cap {color:#9bbfb7 !important;font-size:11px;letter-spacing:.14em;text-transform:uppercase;padding:14px 0 9px;}
    .workspace {color:#deeee9;background:#1c4a51;border:1px solid #40666b;border-radius:12px;padding:12px 14px;font-size:12px;line-height:1.55;}
    .workspace b {color:#e0fff1;}
    .headerover {font-size:12px;letter-spacing:.14em;font-weight:800;color:#0a9b7d;text-transform:uppercase;margin-bottom:6px;}
    .sectiontitle {font-weight:800;font-size:20px;color:#193540;letter-spacing:-.035em;margin:18px 0 5px;}
    .subtext {color:#71838b;font-size:13px;margin-bottom:18px;}
    .hero {background:radial-gradient(circle at 100% 0%,rgba(48,176,144,.4),transparent 36%),linear-gradient(115deg,#103541,#18565A 62%,#177b65);border:1px solid #267b72;border-radius:24px;padding:32px 36px;color:white;position:relative;overflow:hidden;min-height:223px;margin-bottom:17px;}
    .hero:after {content:'';position:absolute; width:340px;height:340px;border:1px solid #ffffff2b;border-radius:50%;right:-75px;top:-150px;box-shadow:0 0 0 47px #ffffff06,0 0 0 105px #ffffff08;pointer-events:none;}
    .hero .eyebrow {color:#b6f9df;font-size:11px;letter-spacing:.16em;font-weight:800;text-transform:uppercase;margin-bottom:14px;}
    .hero h1 {color:#fff !important;font-size:33px !important;line-height:1.2;max-width:670px;margin:0 0 12px;}
    .hero p {color:#cde7e2;font-size:15px;max-width:570px;line-height:1.7;}
    .hero-chip {display:inline-block;color:#dffdf1;background:#ffffff20;border:1px solid #ffffff35;border-radius:25px;font-size:12px;padding:7px 12px;margin-top:8px;}
    .statsbox {background:#fff;padding:22px 24px;border:1px solid #e8edef;border-radius:18px;box-shadow:0 6px 22px #152c3510;min-height:134px;}
    .statslabel {color:#697e86;font-size:12px;font-weight:700;}
    .statsvalue {color:#14343c;font-family:'Manrope',sans-serif;font-weight:800;font-size:29px;letter-spacing:-.05em;margin-top:15px;white-space:nowrap;}
    .statsfoot {font-size:11px;color:#8b9ca2;margin-top:5px;}
    .statpositive {color:#0e997e;}
    .panel {background:#fff;border:1px solid #e6ecee;border-radius:20px;padding:22px 24px;margin-bottom:16px;box-shadow:0 6px 18px #182d3508;}
    .panel-title {font-size:16px;font-weight:800;color:#1b3740;margin-bottom:8px;}
    .muted {font-size:12px;color:#71838b;line-height:1.5;}
    .pill {display:inline-block;font-size:11px;font-weight:800;letter-spacing:.025em;background:#e4f5ef;color:#08775f;padding:6px 11px;border-radius:40px;}
    .pill.amber {background:#fff0df;color:#a86f20;}
    .pill.gray {background:#eff3f4;color:#61727a;}
    .insight {background:#ffffff;border:1px solid #e4ebed;border-radius:16px;padding:18px 18px 15px;margin-bottom:10px;}
    .insight-title {font-size:15px;color:#193841;font-weight:800;line-height:1.4;}
    .insight-description {color:#6f8188;font-size:12px;margin-top:7px;line-height:1.55;}
    .insight-money {font-size:17px;color:#07866d;font-weight:800;margin-top:12px;}
    .subline {height:1px;background:#edf1f2;margin:12px 0;}
    .tag {display:inline-block;color:#678087;background:#edf4f3;font-size:11px;padding:4px 9px;border-radius:8px;font-weight:700;}
    .empty {border:1px dashed #c7d7da;background:#fff;border-radius:19px;padding:40px 20px;text-align:center;color:#617982;}
    .empty strong {display:block;color:#25424b;font-size:19px;margin-bottom:8px;}
    .tiny {font-size:11px;color:#7b9096;line-height:1.55;}
    .callout {background:#e7f6f1;border:1px solid #b7e5d4;border-radius:15px;padding:16px 18px;color:#24574c;font-size:13px;line-height:1.7;}
    .progressbg {background:#e8eff0;border-radius:9px;height:9px;overflow:hidden;margin-top:10px;}
    .progressfill {background:linear-gradient(90deg,#0b907c,#4bcbb0);height:100%;border-radius:9px;}
    .footnote {font-size:11px;color:#819199;line-height:1.6;padding-top:8px;}
    /* ACCESSIBILITY: Button styling is fully scoped so labels stay legible on every page.
       Streamlit may wrap button labels in nested nodes, so propagate the intended color to all descendants. */
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button {
        border-radius:12px !important;font-weight:800 !important;font-size:15px !important;line-height:1.2 !important;
        min-height:46px;padding:.72rem 1rem !important;letter-spacing:-.01em;box-shadow:0 1px 2px rgba(10,34,41,.04);
        transition:background-color .16s ease,border-color .16s ease,box-shadow .16s ease,transform .05s ease;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button * {
        color:inherit !important;-webkit-text-fill-color:currentColor !important;font-weight:inherit !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:not(:disabled):hover {
        box-shadow:0 6px 18px rgba(8,67,64,.12) !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:not(:disabled):active {
        transform:translateY(1px);
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:is([kind="primary"],[data-testid="stBaseButton-primary"]):not(:disabled) {
        background:#0a7f69 !important;border:1px solid #0a7f69 !important;color:#ffffff !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:is([kind="primary"],[data-testid="stBaseButton-primary"]):not(:disabled):hover {
        background:#086452 !important;border-color:#086452 !important;color:#ffffff !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:is([kind="secondary"],[data-testid="stBaseButton-secondary"]):not(:disabled) {
        background:#ffffff !important;color:#14343c !important;border:1px solid #87a9ad !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:is([kind="secondary"],[data-testid="stBaseButton-secondary"]):not(:disabled):hover {
        background:#e9f6f2 !important;border-color:#0a7f69 !important;color:#14343c !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:disabled {
        background:#dceae6 !important;color:#47615e !important;border:1px solid #b4cbc5 !important;cursor:not-allowed;
        box-shadow:none !important;
    }
    :is(div.stButton,div.stFormSubmitButton,div.stDownloadButton)>button:focus-visible {
        outline:3px solid #58dbc0 !important;outline-offset:3px !important;
    }
    /* Workspace switcher uses regular buttons for reliable contrast in the sidebar. */
    [data-testid="stSidebar"] .workspace-toggle-row {margin-bottom:6px;}
    [data-testid="stSidebar"] .workspace-toggle-row :is(div.stButton,div.stFormSubmitButton)>button {
        min-height:48px !important;border-radius:12px !important;font-size:14px !important;
    }
    [data-testid="stFileUploader"] {border-radius:15px;}
    [data-testid="stMetric"] {background:#fff;border-radius:14px;padding:14px;border:1px solid #e6ecee;}
    [data-testid="stTabs"] button {font-weight:700;}
    [data-testid="stDataFrame"] {border:1px solid #e5ecee;border-radius:14px;overflow:hidden;}
    @media(max-width:800px){.hero{padding:24px 23px;min-height:175px}.hero h1{font-size:25px!important}.statsvalue{font-size:24px}.statsbox{min-height:112px;padding:19px}}
    </style>""",unsafe_allow_html=True)

def txt(t): st.markdown(t,unsafe_allow_html=True)
def section(name,sub=""):
    txt(f'<div class="sectiontitle">{h(name)}</div>'+ (f'<div class="subtext">{h(sub)}</div>' if sub else ''))
def stat(title,value,foot="",positive=False):
    txt(f'<div class="statsbox"><div class="statslabel">{h(title)}</div><div class="statsvalue {"statpositive" if positive else ""}">{h(value)}</div><div class="statsfoot">{h(foot)}</div></div>')
def empty(title,sub): txt(f'<div class="empty"><strong>{h(title)}</strong>{h(sub)}</div>')
def indicator(title,desc,amount=None,tag=None):
    value = f'<div class="insight-money">{h(amount)}</div>' if amount else ''
    badge = f'<span class="tag">{h(tag)}</span>' if tag else ''
    txt(f'<div class="insight"><div class="insight-title">{h(title)}</div><div class="insight-description">{h(desc)}</div>{value}<div style="margin-top:10px">{badge}</div></div>')

def df_table(records,fields):
    if not records:
        return empty("Nothing here yet","New entries will appear when you add them.")
    st.dataframe(pd.DataFrame([{header:(fn(r) if callable(fn) else r.get(fn,"")) for header,fn in fields} for r in records]),hide_index=True,use_container_width=True)

def linechart(months):
    if not months: return empty("No spending history","Import transactions to populate this chart.")
    months=months[-8:]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=[x["month"] for x in months],y=[x["spend"]/100 for x in months],mode="lines+markers",fill="tozeroy",line=dict(color="#149b82",width=3,shape="spline"),marker=dict(size=7,color="#ffffff",line=dict(color="#119980",width=2)),fillcolor="rgba(27,172,138,.10)",hovertemplate="%{x}<br>Spent $%{y:,.2f}<extra></extra>"))
    fig.update_layout(margin=dict(l=4,r=12,t=12,b=8),height=266,showlegend=False,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans",color="#70868b",size=11),xaxis=dict(showgrid=False,zeroline=False),yaxis=dict(showgrid=True,gridcolor="#eef3f4",tickprefix="$",zeroline=False))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

def donutchart(cats):
    if not cats: return empty("No categories yet","Your spending mix will appear here.")
    vals=list(cats.items())[:7]
    fig=go.Figure(data=[go.Pie(labels=[x[0] for x in vals],values=[x[1] for x in vals],hole=.69,marker=dict(colors=[COLORS.get(x[0],"#728d97") for x in vals]),textinfo="none",hovertemplate="%{label}: $%{value:,.0f}<extra></extra>")])
    fig.update_layout(height=255,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="rgba(0,0,0,0)",showlegend=True,legend=dict(font=dict(size=10,color="#687f85"),orientation="h",y=-.13,x=0),annotations=[dict(text="SPEND MIX",x=.5,y=.52,font=dict(size=12,color="#54737c"),showarrow=False)],font=dict(family="DM Sans"))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

def data_load(conn):
    return (rows(conn,"SELECT * FROM transactions ORDER BY occurred_on DESC, id DESC"),
            rows(conn,"SELECT * FROM recurring ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, amount_cents DESC"),
            rows(conn,"SELECT * FROM actions ORDER BY created_at DESC, id DESC"),
            rows(conn,"SELECT * FROM budgets"),rows(conn,"SELECT * FROM goals ORDER BY id DESC"))

def load_ui():
    style()
    if "mode" not in st.session_state: st.session_state["mode"]="demo"
    with st.sidebar:
        txt('<div class="brandline"><div class="brandmark">◈</div><div><div class="brandtitle">keepmore<span style="color:#49d9b2">.</span></div><div class="brandsub">Money, made clearer</div></div></div>')
        txt('<div class="sidebar-cap">WORKSPACE</div>')
        ws1, ws2 = st.columns(2, gap="small")
        with ws1:
            demo_clicked = st.button("Explore demo", key="workspace_demo", type="primary" if st.session_state["mode"]=="demo" else "secondary", use_container_width=True)
        with ws2:
            personal_clicked = st.button("My money", key="workspace_personal", type="primary" if st.session_state["mode"]=="personal" else "secondary", use_container_width=True)
        target_mode = "demo" if demo_clicked else "personal" if personal_clicked else None
        if target_mode and target_mode != st.session_state["mode"]:
            st.session_state["mode"] = target_mode
            st.session_state.pop("selected_plan", None)
            st.rerun()
        txt('<div class="sidebar-cap">NAVIGATE</div>')
        destination=st.session_state.pop("navigate_to",None)
        if destination in NAV:
            st.session_state["nav"]=destination
        page=st.radio("Navigation",NAV, label_visibility="collapsed",key="nav")
        st.divider()
        txt(f'<div class="workspace"><b>{"DEMO WORKSPACE" if st.session_state["mode"]=="demo" else "PERSONAL WORKSPACE"}</b><div>{"Fictional sample data. Nothing here is yours." if st.session_state["mode"]=="demo" else "Stored locally in SQLite on this device or server."}</div></div>')
        st.caption("KeepMore • Streamlit MVP 0.1.2")
    return page

def overview(conn,tx,rec,acts,budgets,goals):
    name=get_setting(conn,"display_name","friend")
    current=TODAY.strftime("%Y-%m")
    this=[t for t in tx if t["occurred_on"][:7]==current]
    spending=sum(-t["amount_cents"] for t in this if t["amount_cents"]<0)
    income=sum(t["amount_cents"] for t in this if t["amount_cents"]>0)
    active=[r for r in rec if r["status"]=="active"]
    recurring_monthly=round(sum(monthly_equivalent(r["amount_cents"],r["cycle"]) for r in active))
    opps=opportunities(rec,tx)
    potential=sum(o["annual_cents"] for o in opps)
    tracked=actions_savings(acts)
    due=sorted([(next_due(date.fromisoformat(r["next_due"]),r["cycle"],TODAY),r) for r in active],key=lambda item:item[0])
    upcoming=[x for x in due if (x[0]-TODAY).days<=14]
    txt(f'<div class="headerover">YOUR FINANCIAL HOME · {h(TODAY.strftime("%B %Y").upper())}</div>')
    txt(f'<div class="hero"><div class="eyebrow">THE KEEP MORE DASHBOARD</div><h1>Good to see you, {h(name)}.<br>Give every dollar a better job.</h1><p>Your bills, spending, and next smart move, together in one clear view. Review the opportunities before making changes.</p><span class="hero-chip">{len(opps)} opportunities to review</span></div>')
    if not tx and not rec:
        txt('<div class="callout"><b>Your first five minutes:</b> Add a bill you pay regularly or import a sample bank CSV. KeepMore will start analyzing the recurring costs you identify.</div>')
        q1,q2=st.columns(2)
        with q1:
            if st.button("Add my first bill",type="primary",use_container_width=True,key="onboard_bill"):
                st.session_state["navigate_to"]="Recurring";st.rerun()
        with q2:
            if st.button("Import spending history",use_container_width=True,key="onboard_import"):
                st.session_state["navigate_to"]="Transactions";st.rerun()
    c1,c2,c3,c4=st.columns(4)
    with c1:stat("Spent this month",money(spending),"Recorded outgoing payments")
    with c2:stat("Monthly commitments",money(recurring_monthly),f"{len(active)} active recurring items")
    with c3:stat("Potential annual savings",money(potential),"Opportunities, not guaranteed",True)
    with c4:stat("Reported annual savings",money(tracked),"Completed actions at annual rate",True)
    left,right=st.columns([1.65,1],gap="large")
    with left:
        section("Your spending trend","Recorded outflows over recent months")
        with st.container(border=True):
            linechart(monthly_totals(tx))
        section("Your next money moves","Based on your own entries")
        if opps:
            for o in opps[:3]:
                indicator(o["title"],o["reason"],money(o["annual_cents"])+" / year potential" if o["annual_cents"] else None,o["kind"])
            if st.button("See every opportunity",type="primary",use_container_width=True,key="home_opps"):
                st.session_state["navigate_to"]="Money moves";st.rerun()
        else:empty("No savings flags yet","Mark a subscription 'Not using', import bank transactions, or add recurring bills to get more relevant insights.")
    with right:
        section("Where your money went","This month's spending by category")
        with st.container(border=True):
            donutchart(category_spend(tx,current))
        section("Coming up","Due in the next 14 days")
        with st.container(border=True):
            if upcoming:
                for when,item in upcoming[:5]:
                    days=(when-TODAY).days
                    txt(f'<div style="display:flex;justify-content:space-between;gap:8px;padding:11px 0;border-bottom:1px solid #f0f2f3"><div><div style="font-size:13px;color:#203c45;font-weight:800">{h(item["merchant"])}</div><div class="tiny">{"Today" if days==0 else "Tomorrow" if days==1 else f"In {days} days"} · {h(when.strftime("%b %d"))}</div></div><div style="font-weight:800;color:#193c43;white-space:nowrap">{money(item["amount_cents"])}</div></div>')
            else:
                txt('<div class="muted">No recurring charges due in the next 14 days.</div>')
    txt('<div class="footnote">Data reflects the selected workspace. Potential savings are scenarios. Recorded savings are self-reported annualized amounts, not verified financial results.</div>')

def opportunity_page(conn,tx,rec,acts):
    section("Money moves","Evidence-backed actions for lowering your household costs")
    opps=opportunities(rec,tx)
    monthly=round(sum(monthly_equivalent(r["amount_cents"],r["cycle"]) for r in rec if r["status"]=="active"))
    c1,c2,c3=st.columns(3)
    with c1:stat("Items to review",str(len(opps)),"Ranked by relevance")
    with c2:stat("At-risk opportunity",money(sum(x["annual_cents"] for x in opps)),"Possible annual reduction",True)
    with c3:stat("Monthly commitments",money(monthly),"Across active plans")
    st.markdown(" ")
    tab1,tab2=st.tabs(["Your opportunities","Action history"])
    with tab1:
        if not opps:
            empty("No opportunities flagged yet","Your personalized opportunities will appear after you add recurring expenses or import payment history.")
        for o in opps:
            with st.container(border=True):
                l,r=st.columns([3,1])
                with l:
                    st.markdown(f"#### {o['title']}")
                    st.write(o["reason"])
                    st.caption(f"Source: {o['evidence']}. Verify your terms and actual options before acting.")
                with r:
                    st.metric("Annual potential",money(o["annual_cents"]))
                sub=next((s for s in rec if s["id"]==o["recurring_id"]),None)
                if sub:
                    if st.button("Build an action plan",key="plan_"+o["key"],type="primary"):
                        st.session_state["selected_plan"]=(sub["id"],o["kind"])
                if st.session_state.get("selected_plan")== (o["recurring_id"],o["kind"]):
                    st.info("The message below is a draft to contact your provider. It does not cancel, change, or negotiate your account.")
                    inc=detect_price_increase(sub["merchant"],tx,sub["amount_cents"])
                    st.code(script_for(sub["merchant"],sub["amount_cents"],o["kind"],inc["old_cents"] if inc else None),language=None)
                    with st.form("takeaction"+o["key"]):
                        after=st.number_input("Expected new charge, per current billing cycle ($)",0.0,100000.0,0.0 if o["kind"]=="Cancel or pause" else float(sub["amount_cents"])/100,step=1.0)
                        note=st.text_input("Your next step",placeholder="e.g. Call on Tuesday to ask about price match")
                        submitted=st.form_submit_button("Save action plan",type="primary")
                        if submitted:
                            duplicate=conn.execute("SELECT id FROM actions WHERE recurring_id=? AND kind=? AND status='planned'",(sub["id"],o["kind"])).fetchone()
                            if duplicate:
                                st.warning("You already have a plan for this item and action type. Finish or dismiss it under Action history.")
                            else:
                                conn.execute("INSERT INTO actions(recurring_id,title,kind,status,before_cents,after_cents,cycle,notes) VALUES(?,?,?,?,?,?,?,?)",(sub["id"],o["title"],o["kind"],"planned",sub["amount_cents"],cents(after),sub["cycle"],note))
                                conn.commit();st.session_state.pop("selected_plan",None);st.success("Plan saved to Action history.");st.rerun()
    with tab2:
        if not acts:empty("Your wins start here","Save a plan, then record its outcome when your provider confirms it.")
        for action in acts:
            with st.container(border=True):
                a,b,c=st.columns([2,1,1])
                with a:
                    st.markdown(f"**{action['title']}**")
                    st.caption(action["notes"] or "No note added")
                with b:st.write(action["status"].capitalize())
                with c:st.write(money(max(0,action["before_cents"]-action["after_cents"])*CYCLES.get(action["cycle"],12))+" / yr")
                if action["status"]=="planned":
                    with st.form(f"result_{action['id']}"):
                        actual=st.number_input("Confirmed charge after the change ($ per cycle)",min_value=0.0,max_value=100000.0,value=action["after_cents"]/100,step=1.0,key=f"actual_{action['id']}")
                        confirmed=st.checkbox("I contacted the provider and am recording the outcome",key=f"confirm_{action['id']}")
                        change_tracker=st.checkbox("Also update the recurring-plan tracker",value=True,key=f"sync_{action['id']}")
                        a,b=st.columns(2)
                        with a: complete=st.form_submit_button("Record completed outcome",type="primary",disabled=not confirmed)
                        with b: dismiss=st.form_submit_button("Dismiss plan")
                        if complete:
                            amount_cents=cents(actual)
                            conn.execute("UPDATE actions SET status='completed',after_cents=?,completed_at=? WHERE id=?",(amount_cents,TODAY.isoformat(),action["id"]))
                            if change_tracker and action["recurring_id"]:
                                if amount_cents == 0:
                                    conn.execute("UPDATE recurring SET status='cancelled' WHERE id=?",(action["recurring_id"],))
                                else:
                                    conn.execute("UPDATE recurring SET amount_cents=? WHERE id=?",(amount_cents,action["recurring_id"]))
                            conn.commit();st.rerun()
                        if dismiss:
                            conn.execute("UPDATE actions SET status='dismissed' WHERE id=?",(action["id"],))
                            conn.commit();st.rerun()
        st.caption("Completed outcomes are based on amounts you entered. A provider confirmation is not independently checked.")

def recurring_page(conn,tx,rec):
    section("Recurring, under control","Track subscriptions, essential bills, and future renewals")
    active=[x for x in rec if x["status"]=="active"]
    monthly=round(sum(monthly_equivalent(r["amount_cents"],r["cycle"]) for r in active))
    c1,c2,c3=st.columns(3)
    with c1:stat("Total every month",money(monthly),"Equivalent recurring cost")
    with c2:stat("Annual commitment",money(monthly*12),"Assuming current rates")
    with c3:stat("Active services",str(len(active)),"Includes housing and bills")
    tab1,tab2,tab3=st.tabs(["Manage recurring","Find recurring","Add a new item"])
    with tab1:
        if not rec:empty("No recurring items yet","Add a plan or detect one from imported transactions.")
        for item in rec:
            with st.expander(f"{item['merchant']} · {money(item['amount_cents'])} / {item['cycle'].lower()} · {item['status']}"):
                with st.form(f"edit_{item['id']}"):
                    n=st.text_input("Merchant / plan",item["merchant"])
                    c1,c2,c3=st.columns(3)
                    with c1:price=st.number_input("Amount per cycle ($)",0.01,100000.0,item["amount_cents"]/100,step=1.0,key=f"price_{item['id']}")
                    with c2:cycle=st.selectbox("Cycle",list(CYCLES),index=list(CYCLES).index(item["cycle"]),key=f"cycle_{item['id']}")
                    with c3:due=st.date_input("Next due",date.fromisoformat(item["next_due"]),key=f"due_{item['id']}")
                    c1,c2,c3=st.columns(3)
                    with c1:usage=st.selectbox("How often do you use it?",["Not rated","Essential","Use it","Not using"],index=["Not rated","Essential","Use it","Not using"].index(item["usage"]),key=f"use_{item['id']}")
                    with c2:cat=st.selectbox("Category",CATEGORIES,index=CATEGORIES.index(item["category"]) if item["category"] in CATEGORIES else CATEGORIES.index("Other"),key=f"cat_{item['id']}")
                    with c3:status=st.selectbox("Status",["active","paused","cancelled"],index=["active","paused","cancelled"].index(item["status"]),key=f"status_{item['id']}")
                    st.caption("Changing a status updates your tracker only. It does not contact the merchant.")
                    if st.form_submit_button("Save changes",type="primary"):
                        if n.strip():
                            conn.execute("UPDATE recurring SET merchant=?,amount_cents=?,cycle=?,next_due=?,usage=?,category=?,status=? WHERE id=?",(n.strip(),cents(price),cycle,due.isoformat(),usage,cat,status,item["id"]))
                            conn.commit();st.rerun()
                        else:st.error("Enter a plan name.")
    with tab2:
        candidates=detect_recurring(tx,rec,TODAY)
        st.caption("We look for three or more evenly spaced payments. Each suggestion requires your review. Detection works best with several months of transactions.")
        if not candidates:empty("No new recurring patterns found","Import a few months of transactions or create a plan manually.")
        for i,x in enumerate(candidates):
            with st.container(border=True):
                a,b,c=st.columns([2,1,1])
                with a:st.markdown(f"**{x['merchant']}**");st.caption(f"{x['payments']} observed payments · {x['confidence']} confidence")
                with b:st.markdown(money(x["amount_cents"]));st.caption(x["cycle"])
                with c:
                    if st.button("Track this",key=f"candidate{i}",type="primary"):
                        add_recurring(conn,x["merchant"],x["category"],x["amount_cents"],x["cycle"],x["next_due"],origin="detected")
                        conn.commit();st.rerun()
    with tab3:
        with st.form("new_recurring",clear_on_submit=True):
            name=st.text_input("Company or plan name",placeholder="Internet, gym, streaming, rent...")
            a,b,c=st.columns(3)
            with a:amt=st.number_input("Payment amount ($)",min_value=0.01,value=19.99,step=1.0)
            with b:cycle=st.selectbox("Billing frequency",list(CYCLES),index=2)
            with c:due=st.date_input("Next due date",TODAY)
            a,b=st.columns(2)
            with a:cat=st.selectbox("Category",CATEGORIES,index=CATEGORIES.index("Subscriptions"))
            with b:use=st.selectbox("How often do you use it?",["Not rated","Essential","Use it","Not using"])
            if st.form_submit_button("Add recurring item",type="primary"):
                if name.strip():
                    add_recurring(conn,name,cat,cents(amt),cycle,due.isoformat(),use)
                    conn.commit();st.rerun()
                else:st.error("Please enter a company or plan name.")

def csv_records_to_bytes(records):
    if not records:return b""
    def spreadsheet_safe(v):
        if isinstance(v,str) and v.lstrip().startswith(("=","+","-","@")):
            return "'"+v
        return v
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(records[0]));writer.writeheader()
    for record in records:
        writer.writerow({key:spreadsheet_safe(value) for key,value in record.items()})
    return out.getvalue().encode("utf-8-sig")

def transaction_page(conn,tx):
    section("Every dollar, accounted for","A flexible ledger with a safe CSV import workflow")
    tab1,tab2,tab3,tab4=st.tabs(["Transactions","Import CSV","Add manually","Read a bill PDF"])
    with tab1:
        a,b,c=st.columns([2,1,1])
        with a:q=st.text_input("Find a merchant",placeholder="Search merchant or description")
        with b:filter_cat=st.selectbox("Category",["All"]+CATEGORIES)
        with c:period=st.selectbox("Time",["All time","This month","Last 90 days"])
        visible=[x for x in tx if (not q or q.lower() in x["merchant"].lower()) and (filter_cat=="All" or x["category"]==filter_cat) and (period=="All time" or (period=="This month" and x["occurred_on"][:7]==TODAY.strftime("%Y-%m")) or (period=="Last 90 days" and x["occurred_on"] >= (TODAY-timedelta(days=90)).isoformat()))]
        df_table(visible,[('Date','occurred_on'),('Merchant','merchant'),('Category','category'),('Amount',lambda r:money(r['amount_cents'])),('Source','source')])
        if visible:
            st.download_button("Export filtered transactions (CSV)",csv_records_to_bytes(visible),"keepmore_transactions.csv","text/csv",use_container_width=True)
        with st.expander("Correct a transaction's details"):
            if tx:
                options={f"#{r['id']} · {r['occurred_on']} · {r['merchant']} · {money(r['amount_cents'])}":r for r in tx}
                selected=st.selectbox("Select transaction to edit",list(options),key="edit_tx_sel")
                item=options[selected]
                with st.form(f"edit_tx_{item['id']}"):
                    a,b=st.columns(2)
                    with a: new_date=st.date_input("Date",date.fromisoformat(item["occurred_on"]))
                    with b: new_category=st.selectbox("Category",CATEGORIES,index=CATEGORIES.index(item["category"]) if item["category"] in CATEGORIES else CATEGORIES.index("Other"))
                    description=st.text_input("Merchant",value=item["merchant"])
                    amt=st.number_input("Signed amount ($). Negative means expense",value=item["amount_cents"]/100,step=1.0)
                    note=st.text_input("Note",value=item["note"])
                    if st.form_submit_button("Save corrected transaction",type="primary"):
                        if not description.strip() or cents(amt)==0:
                            st.error("Merchant and nonzero amount are required.")
                        else:
                            conn.execute("UPDATE transactions SET occurred_on=?,category=?,merchant=?,amount_cents=?,note=? WHERE id=?",(new_date.isoformat(),new_category,description.strip()[:160],cents(amt),note[:500],item["id"]))
                            conn.commit();st.rerun()
        with st.expander("Remove a transaction"):
            if tx:
                options={f"#{r['id']} · {r['occurred_on']} · {r['merchant']} · {money(r['amount_cents'])}":r['id'] for r in tx}
                selected=st.selectbox("Select transaction",list(options))
                sure=st.checkbox("I want to remove this entry")
                if st.button("Delete selected transaction",disabled=not sure):
                    conn.execute("DELETE FROM transactions WHERE id=?",(options[selected],));conn.commit();st.rerun()
    with tab2:
        uploaded=st.file_uploader("Choose a bank or credit-card CSV",type=["csv"],key="csv_import")
        st.caption("KeepMore does not connect to your bank. Your statement stays in your selected workspace. Do not upload passwords, account numbers, or ID scans.")
        if uploaded:
            raw=uploaded.getvalue()
            if len(raw)>15_000_000: st.error("CSV exceeds the 15 MB limit.")
            else:
                try:
                    import hashlib
                    sha=hashlib.sha256(raw).hexdigest()
                    prior=conn.execute("SELECT name FROM imports WHERE sha256=?",(sha,)).fetchone()
                    if prior:st.warning(f"This exact file was imported earlier as {prior['name']}.")
                    preview_df=pd.read_csv(io.BytesIO(raw),dtype=str,keep_default_na=False,encoding="utf-8-sig")
                    cols=list(preview_df.columns)
                    if len(cols)<3:
                        st.error("CSV needs at least three columns.")
                    else:
                        st.dataframe(preview_df.head(5),use_container_width=True,hide_index=True)
                        st.markdown("##### Match your columns")
                        def preferred(terms,exclude=[]):
                            for x in cols:
                                if any(term in x.lower() for term in terms) and x not in exclude:return x
                            return cols[0]
                        a,b=st.columns(2)
                        with a:date_col=st.selectbox("Date column",cols,index=cols.index(preferred(["date","posted"])))
                        with b:desc_col=st.selectbox("Merchant / description",cols,index=cols.index(preferred(["description","merchant","payee","name"])))
                        separate=st.checkbox("My file uses separate debit and credit columns")
                        mapping={"date":date_col,"description":desc_col}
                        if separate:
                            a,b=st.columns(2)
                            with a:mapping["debit"]=st.selectbox("Debit (money out)",cols,index=cols.index(preferred(["debit","withdrawal","paid"])))
                            with b:mapping["credit"]=st.selectbox("Credit (money in)",cols,index=cols.index(preferred(["credit","deposit"])))
                            sign="negative"
                        else:
                            mapping["amount"]=st.selectbox("Amount column",cols,index=cols.index(preferred(["amount","value","total"])))
                            sign=st.radio("Your file's sign convention",["negative","positive"],format_func=lambda x:"Negative = money out, positive = money in" if x=="negative" else "Positive = money out, negative = money in",horizontal=True)
                        cat_col=st.selectbox("Category column (optional)",["None"]+cols)
                        if cat_col!="None":mapping["category"]=cat_col
                        dayfirst=st.checkbox("Dates are day / month / year",value=False)
                        parsed,errors=parse_csv(raw,mapping,sign,dayfirst)
                        st.info(f"Ready: {len(parsed):,} valid rows · {len(errors):,} rejected rows. Check sign direction before importing.")
                        df_table(parsed[:5],[('Date','occurred_on'),('Merchant','merchant'),('Amount',lambda r:money(r['amount_cents'])),('Category','category')])
                        if errors:
                            with st.expander(f"Preview {len(errors)} import errors"):
                                st.write("\n".join(errors[:30]))
                        if st.button("Import reviewed rows",type="primary",disabled=bool(prior) or not parsed):
                            for r in parsed:add_transaction(conn,r["occurred_on"],r["merchant"],r["category"],r["amount_cents"],r["note"],"csv",sha)
                            conn.execute("INSERT INTO imports(sha256,name,row_count) VALUES(?,?,?)",(sha,uploaded.name,len(parsed)))
                            conn.commit();st.success(f"Imported {len(parsed):,} rows.");st.rerun()
                except Exception as exc:st.error(f"Unable to read this CSV: {str(exc)[:180]}")
        with st.expander("CSV format example"):
            st.code("date,description,amount\n2026-09-03,Grocery Store,-64.50\n2026-09-04,Paycheck,2200.00\n2026-09-05,Internet Provider,-79.99",language="csv")
    with tab3:
        with st.form("add_transaction",clear_on_submit=True):
            a,b=st.columns(2)
            with a:on=st.date_input("Transaction date",TODAY,key="new_tx_date")
            with b:direction=st.selectbox("Type",["Expense","Income"])
            merchant=st.text_input("Merchant or source",placeholder="Grocery store, salary, refund...")
            a,b=st.columns(2)
            with a:amount=st.number_input("Amount ($)",min_value=0.01,value=25.00,step=1.0)
            with b:cat=st.selectbox("Category",CATEGORIES,index=1)
            notes=st.text_input("Optional note")
            if st.form_submit_button("Save transaction",type="primary"):
                if merchant.strip():
                    add_transaction(conn,on.isoformat(),merchant,cat,cents(amount)*(-1 if direction=="Expense" else 1),notes)
                    conn.commit();st.rerun()
                else:st.error("Enter a merchant or source.")
    with tab4:
        st.write("Extract selectable text from a bill PDF and review its due date and amount. Files are processed in memory. No file is stored.")
        pdf=st.file_uploader("Select a bill PDF (text-based)",type=["pdf"])
        if pdf:
            try:
                reader=PdfReader(io.BytesIO(pdf.getvalue()))
                text_content="\n".join((p.extract_text() or "") for p in reader.pages[:5])[:20000]
                if not text_content.strip():st.warning("This PDF contains no selectable text. Image-only scans need OCR in a future release.")
                else:
                    amount_matches=re.findall(r"(?:total\s+(?:amount\s+)?due|amount\s+due|balance\s+due)\s*[:\s]*\$?\s*([\d,]+\.\d\d)",text_content,re.I)
                    due_match=re.search(r"(?:payment\s+due|due\s+date)\s*[:\s]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",text_content,re.I)
                    st.caption("Extracted excerpt (verify against the original PDF)")
                    st.code(re.sub(r"\s+"," ",text_content)[:450],language=None)
                    with st.form("pdf_to_bill"):
                        n=st.text_input("Confirm bill company",value=Path(pdf.name).stem.replace("_"," ")[:70])
                        a,b=st.columns(2)
                        with a:bill_amt=st.number_input("Confirm amount due ($)",min_value=0.01,value=float(amount_matches[0].replace(",","")) if amount_matches else 40.0,step=1.0)
                        with b:bill_date=st.date_input("Confirm due date",value=TODAY+timedelta(days=7))
                        cycle=st.selectbox("Repeat interval",list(CYCLES),index=2)
                        cat=st.selectbox("Category",CATEGORIES,index=CATEGORIES.index("Utilities"))
                        if st.form_submit_button("Track confirmed bill",type="primary"):
                            add_recurring(conn,n,cat,cents(bill_amt),cycle,bill_date.isoformat(),note="Reviewed from PDF")
                            conn.commit();st.rerun()
                    if due_match:st.caption(f"Possible due date in PDF: {due_match.group(1)}. Confirm manually before saving.")
            except Exception as exc:st.error(f"PDF text could not be read: {str(exc)[:140]}")

def bills_page(conn,rec):
    section("Never be surprised by a renewal","Your upcoming charges and downloadable calendar reminders")
    active=[r for r in rec if r["status"]=="active"]
    due=sorted([(next_due(date.fromisoformat(r["next_due"]),r["cycle"],TODAY),r) for r in active],key=lambda x:x[0])
    horizon=st.segmented_control("Look ahead",["14 days","30 days","90 days"],default="30 days")
    num=int((horizon or "30 days").split()[0])
    showing=[(d,r) for d,r in due if (d-TODAY).days<=num]
    c1,c2=st.columns(2)
    with c1:stat("Due in selected window",str(len(showing)),f"Next {num} days")
    with c2:stat("Total expected",money(sum(r["amount_cents"] for _,r in showing)),"Single upcoming date per plan")
    st.markdown(" ")
    if not showing:empty("No items in this window","Add recurring bills to your workspace to see reminders.")
    for when,r in showing:
        with st.container(border=True):
            a,b,c=st.columns([2,1,1])
            with a:st.markdown(f"**{r['merchant']}**");st.caption(f"{r['category']} · {r['cycle']} · {r['status']}")
            with b:st.write(when.strftime("%a, %b %d"));st.caption(f"{(when-TODAY).days} day(s) away")
            with c:st.markdown(f"**{money(r['amount_cents'])}**")
    if due:
        st.download_button("Download calendar file (.ics)",calendar_ics(active),"keepmore_bill_dates.ics","text/calendar",type="primary",use_container_width=True)
    st.caption("Calendar export creates one reminder per active bill using its next estimated due date. This version does not send push notifications or monitor providers automatically.")

def budgets_page(conn,tx,budgets):
    section("Budget studio","Give your essentials room and spot pressure early")
    current=TODAY.strftime("%Y-%m")
    actual=category_spend(tx,current)
    limit={r["category"]:r["limit_cents"] for r in budgets}
    income=int(get_setting(conn,"monthly_income","0") or "0")
    month_tx=[r for r in tx if r["occurred_on"][:7]==current]
    spent=sum(-r["amount_cents"] for r in month_tx if r["amount_cents"]<0)
    plan_total=sum(limit.values())
    a,b,c=st.columns(3)
    with a:stat("Monthly income target",money(income),"Entered by you")
    with b:stat("Spent this month",money(spent),"Recorded purchases and bills")
    with c:stat("Planned flexible spend",money(plan_total),"Sum of category limits")
    st.markdown(" ")
    a,b=st.columns([1.8,1],gap="large")
    with a:
        section("Category pulse", "Month-to-date spending against your limits")
        if not limit:empty("No budget limits yet","Use the editor to start planning by category.")
        for cat,cap in sorted(limit.items()):
            usage=actual.get(cat,0)
            pct=usage/max(1,cap)*100
            txt(f'<div style="margin:15px 0 23px"><div style="display:flex;justify-content:space-between;gap:12px;font-size:13px;color:#25434c"><b>{h(cat)}</b><span>{money(usage)} <span style="color:#89999d">/ {money(cap)}</span></span></div><div class="progressbg"><div class="progressfill" style="width:{min(100,pct):.1f}%;background:{"#e9a05b" if pct>100 else "linear-gradient(90deg,#0b907c,#4bcbb0)"}"></div></div><div class="tiny">{pct:.0f}% of budget used{" · Over limit" if pct>100 else ""}</div></div>')
        unplanned={k:v for k,v in actual.items() if k not in limit and v>0}
        if unplanned:
            st.caption("Spending outside tracked budget categories: "+money(sum(unplanned.values())))
    with b:
        section("Edit your plan","Your changes save to this workspace")
        with st.form("budget_update"):
            monthincome=st.number_input("Expected monthly household income ($)",min_value=0.0,value=income/100,step=100.0)
            edits={}
            st.markdown("##### Category limits ($ / month)")
            for category in ["Groceries","Dining","Transport","Shopping","Entertainment","Family","Health","Utilities","Housing","Insurance","Subscriptions","Education","Other"]:
                edits[category]=st.number_input(category,min_value=0.0,max_value=1_000_000.0,value=limit.get(category,0)/100,step=25.0,key=f"bdg{category}")
            if st.form_submit_button("Save monthly plan",type="primary",use_container_width=True):
                conn.execute("DELETE FROM budgets")
                for cat,amt in edits.items():
                    if amt>0:conn.execute("INSERT INTO budgets(category,limit_cents) VALUES(?,?)",(cat,cents(amt)))
                setting(conn,"monthly_income",str(cents(monthincome)))
                conn.commit();st.rerun()
        st.caption("Budget planning uses the income value you enter. It does not predict your next paycheck.")

def goals_page(conn,rec,goals):
    section("Goals & decisions","Convert spending choices into a plan for something important")
    tabs=st.tabs(["Your goals","Purchase pause","What-if simulator"])
    with tabs[0]:
        for g in goals:
            with st.container(border=True):
                progress=min(100,g["saved_cents"]/max(1,g["target_cents"])*100)
                a,b=st.columns([3,1])
                with a:
                    st.markdown(f"#### {g['title']}")
                    st.caption(f"{money(g['saved_cents'])} of {money(g['target_cents'])} saved" + (f" · target {g['target_date']}" if g["target_date"] else ""))
                    st.progress(min(1,progress/100),text=f"{progress:.0f}% of target")
                with b:
                    with st.popover(f"Update goal #{g['id']}"):
                        with st.form(f"goal_update_{g['id']}"):
                            saved_total=st.number_input("Current saved balance ($)",min_value=0.0,value=g["saved_cents"]/100,step=25.0,key=f"g_saved_{g['id']}")
                            target_total=st.number_input("Target amount ($)",min_value=1.0,value=g["target_cents"]/100,step=100.0,key=f"g_target_{g['id']}")
                            save=st.form_submit_button("Update goal",type="primary")
                            if save:
                                conn.execute("UPDATE goals SET saved_cents=?,target_cents=? WHERE id=?",(cents(saved_total),cents(target_total),g["id"]))
                                conn.commit();st.rerun()
        with st.expander("Create a new savings goal",expanded=not bool(goals)):
            with st.form("newgoal"):
                name=st.text_input("What are you saving for?",placeholder="Emergency fund, vacation, repairs...")
                a,b,c=st.columns(3)
                with a:target=st.number_input("Goal amount ($)",min_value=1.0,value=1000.0,step=100.0)
                with b:saved=st.number_input("Already saved ($)",min_value=0.0,value=0.0,step=25.0)
                with c:deadline=st.date_input("Target date",add_months(TODAY,12))
                if st.form_submit_button("Create goal",type="primary"):
                    if name.strip():add_goal(conn,name,cents(target),cents(saved),deadline.isoformat());conn.commit();st.rerun()
                    else:st.error("Name your savings goal.")
    with tabs[1]:
        st.markdown("#### Check a purchase against your priorities")
        a,b=st.columns(2)
        with a:cost=st.number_input("Purchase price ($)",min_value=1.0,value=240.0,step=10.0)
        with b:repeat=st.selectbox("How often?",["One time","Every month","Every week","Every year"])
        impact={"One time":cost,"Every month":cost*12,"Every week":cost*52,"Every year":cost}[repeat]
        a,b=st.columns(2)
        with a:stat("First-year outlay",money(round(impact*100)),"No hypothetical investment returns")
        with b:stat("30-day pause value",money(round(cost*100)),"Cash retained if you skip once",True)
        if goals:
            g=st.selectbox("Compare it to a goal",goals,format_func=lambda x:x["title"])
            gap=max(0,g["target_cents"]-g["saved_cents"])
            if gap:st.info(f"Putting the first {money(round(cost*100))} toward {g['title']} would cover {min(100,cost*100/gap):.0f}% of its remaining {money(gap)} gap.")
        st.caption("This is a spending comparison, not a credit or investment recommendation.")
    with tabs[2]:
        st.markdown("#### Your savings scenario")
        active=[r for r in rec if r["status"]=="active"]
        subs=[r for r in active if r["category"] in ["Subscriptions","Entertainment"]]
        optional=round(sum(monthly_equivalent(x["amount_cents"],x["cycle"]) for x in subs))
        st.write(f"Your tracked subscriptions and entertainment plans total {money(optional)} in monthly equivalents.")
        trim=st.slider("Reduction in this category",0,100,20,5)
        monthly=round(optional*trim/100)
        period=st.slider("Months to sustain the change",1,36,12)
        a,b=st.columns(2)
        with a:stat("Monthly room",money(monthly),"Hypothetical reduction")
        with b:stat("Total across period",money(monthly*period),f"Across {period} months",True)
        st.caption("Scenarios show simple arithmetic. Actual offers, behavior, and bills determine whether savings occur.")

def local_answer(question,tx,rec,goals,acts):
    q=question.lower()
    current=TODAY.strftime("%Y-%m")
    cats=category_spend(tx,current)
    total=sum(cats.values())
    active=[r for r in rec if r["status"]=="active"]
    subs=[r for r in active if r["category"] in ["Subscriptions","Entertainment"]]
    due=sorted([(next_due(date.fromisoformat(r["next_due"]),r["cycle"],TODAY),r) for r in active],key=lambda x:x[0])
    opp=opportunities(rec,tx)
    if any(x in q for x in ["subscription","recurring","monthly bill","commitment"]):
        amount=round(sum(monthly_equivalent(x["amount_cents"],x["cycle"]) for x in active))
        optional=round(sum(monthly_equivalent(x["amount_cents"],x["cycle"]) for x in subs))
        return f"You track {len(active)} active recurring plans totaling {money(amount)} per month. Subscriptions and entertainment account for {money(optional)} of that amount. Review the plans marked 'Not using' first."
    if any(x in q for x in ["next bill","due","renewal","upcoming"]):
        if not due:return "You have no active due dates on record. Add a recurring item to start tracking them."
        return "Your next scheduled items are: "+"; ".join(f"{r['merchant']} on {when.strftime('%b %d')} for {money(r['amount_cents'])}" for when,r in due[:4])+". These are tracker dates, not live provider confirmations."
    if any(x in q for x in ["save","reduce","cut","opportunit","cancel"]):
        if not opp:return "I found no flagged savings opportunities yet. Mark your plan usage, or import a few months of transactions to detect price changes."
        return "Top opportunities: "+"; ".join(f"{o['title']} ({money(o['annual_cents'])} in potential annual reduction)" for o in opp[:3])+". Check your contract and provider before acting."
    if any(x in q for x in ["goal","emergency","trip","target"]):
        if not goals:return "No goals saved yet. Open Goals & decisions to set one with a target amount and deadline."
        return "Your savings targets: "+"; ".join(f"{g['title']} {money(g['saved_cents'])} of {money(g['target_cents'])}" for g in goals[:3])+". Choose one goal for your next small contribution."
    if any(x in q for x in ["spent","spend","expens","category","where"]):
        top=sorted(cats.items(),key=lambda x:-x[1])[:3]
        if not top:return "I have no expenses recorded for this month. Import a CSV or add transactions to see where your money goes."
        return f"So far this month, recorded expenses total {money(total)}. The top categories are "+", ".join(f"{k} {money(v)}" for k,v in top)+". The Budget studio shows which categories exceed your plan."
    if any(x in q for x in ["win","saved","completed","result"]):
        return f"Your self-reported completed changes represent {money(actions_savings(acts))} in annualized savings. This is based on your recorded before-and-after amounts."
    return "Try asking: 'Where did my money go this month?', 'What subscriptions do I have?', 'What bills are due next?', 'Where can I save?', or 'How are my goals going?' The offline coach answers within your Streamlit deployment without third-party AI calls."

def ai_page(conn,tx,rec,goals,acts):
    section("Ask KeepMore","A personal money explainer grounded in your own entries")
    txt('<div class="callout"><b>Private by default.</b> The built-in coach uses local calculations within your Streamlit deployment. Optional cloud answers require a configured API key and your per-question consent.</div>')
    st.markdown(" ")
    prompts=["Where did my money go this month?","Where can I save?","What bills are due next?","What subscriptions do I have?","How are my savings goals going?"]
    selection=st.selectbox("Start with a question",["Write my own"]+prompts)
    question=st.text_input("Ask your money question",value="" if selection=="Write my own" else selection,placeholder="e.g. How much am I spending on recurring bills?")
    cloud=bool(os.getenv("OPENAI_API_KEY"))
    if cloud:consent=st.checkbox("Use optional AI answer for this question. Sends only a financial summary plus my question to OpenAI.",value=False)
    else:
        consent=False
        st.caption("Offline guidance is active. Cloud AI is optional and not required to use KeepMore.")
    if st.button("Get my answer",type="primary",disabled=not question.strip()):
        answer=local_answer(question,tx,rec,goals,acts)
        if cloud and consent:
            try:
                from openai import OpenAI
                summary={"month":TODAY.strftime('%Y-%m'),"current_month_category_spend_dollars":{k:round(v/100,2) for k,v in category_spend(tx,TODAY.strftime('%Y-%m')).items()},"recurring_monthly_dollars":round(sum(monthly_equivalent(x["amount_cents"],x["cycle"]) for x in rec if x["status"]=="active")/100,2),"active_plan_count":sum(x["status"]=="active" for x in rec),"potential_actions":len(opportunities(rec,tx)),"goal_count":len(goals)}
                model=os.getenv("KEEPMORE_AI_MODEL","gpt-4.1-mini")
                response=OpenAI(timeout=20).responses.create(model=model,max_output_tokens=350,input=[{"role":"system","content":"You are a careful household expense coach. Be concise and practical. Use only provided aggregate data, do not infer financial facts. Never claim to modify accounts or guarantee savings. If insufficient data, say so. Never give investment, tax or legal instructions."},{"role":"user","content":json.dumps({"question":question,"summary":summary})}])
                answer=response.output_text or answer
                st.caption("Optional AI answer based on aggregate data")
            except Exception as exc:
                st.warning(f"AI service not available. Showing offline answer instead ({type(exc).__name__}).")
        txt('<div class="sectiontitle">Your answer</div>')
        st.markdown(answer)
        st.session_state["last_answer"]=answer
    if st.session_state.get("last_answer"):
        st.download_button("Save latest answer (.txt)",st.session_state["last_answer"].encode(),"keepmore_answer.txt","text/plain")

def settings_page(conn,tx,rec,acts,budgets,goals):
    section("Settings & your data","Control your workspace and shape the product")
    tab1,tab2,tab3=st.tabs(["My preferences","Your data","Pricing & early access"])
    with tab1:
        with st.form("preferences"):
            name=st.text_input("Display name",value=get_setting(conn,"display_name",""),max_chars=40)
            currency=st.selectbox("Currency",["USD ($)"],help="The MVP supports US dollar calculations.")
            if st.form_submit_button("Save preferences",type="primary"):
                setting(conn,"display_name",name.strip()[:40] or "friend");conn.commit();st.rerun()
        st.caption(f"Active workspace: {st.session_state['mode'].capitalize()}. Data file: {path_for(st.session_state['mode'],DATA_DIR).name}.")
    with tab2:
        st.markdown("#### Your records belong to you")
        st.write("Transactions, recurring plans, goals, action outcomes, and budgets remain in the SQLite file for this workspace.")
        backup=export_database(conn)
        st.download_button("Export full workspace (JSON)",json.dumps(backup,indent=2,default=str).encode(),"keepmore_backup.json","application/json",type="primary")
        st.caption("Download a copy before deleting local data. The file contains personal finance details.")
        with st.expander("Delete all data in this workspace"):
            st.warning("This permanently clears transactions, recurring plans, budgets, goals, import history, and contact interest for the selected workspace.")
            phrase=st.text_input("Type DELETE to confirm",key="delete_all")
            if st.button("Permanently clear workspace",disabled=phrase!="DELETE"):
                clear_workspace(conn)
                if st.session_state["mode"]=="demo":setting(conn,"seeded","1")
                conn.commit();st.rerun()
    with tab3:
        st.markdown("#### KeepMore Pro, planned")
        txt('<div class="panel"><div class="panel-title">Free essentials</div><div class="muted">Manual transactions, CSV uploads, budget snapshots, recurring tracking, calendar export, goals, and offline money coach.</div><div class="subline"></div><div class="panel-title">Pro concept · $5.99 / month or $49 / year</div><div class="muted">Planned features: cross-device sync, automated reminders, sharing for couples, premium reports, and more advanced document analysis. This version does not charge or activate a subscription.</div></div>')
        st.write("Interested in testing premium tools? Record your interest in this workspace.")
        with st.form("early_access"):
            email=st.text_input("Email",placeholder="you@example.com")
            plan=st.radio("Preferred option",["$5.99/month","$49/year","Free only"],horizontal=True)
            agree=st.checkbox("I agree to store this email locally in the active workspace")
            if st.form_submit_button("Record my interest",type="primary"):
                if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):st.error("Enter a valid email address.")
                elif not agree:st.error("Confirm local storage to continue.")
                else:
                    conn.execute("INSERT INTO interest(email,plan) VALUES(?,?) ON CONFLICT(email) DO UPDATE SET plan=excluded.plan",(email.strip().lower(),plan));conn.commit();st.success("Interest saved in this local workspace. No email was sent or subscription activated.")
        st.caption("To run a real paid service, implement authentication, a private hosted database, a billing provider with webhooks, and a tested entitlement system first.")

def main():
    page=load_ui()
    path=path_for(st.session_state["mode"],DATA_DIR)
    with db(path) as conn:
        if st.session_state["mode"]=="demo":
            seed(conn,TODAY);conn.commit()
        tx,rec,acts,budgets,goals=data_load(conn)
        if page=="Overview":overview(conn,tx,rec,acts,budgets,goals)
        elif page=="Money moves":opportunity_page(conn,tx,rec,acts)
        elif page=="Recurring":recurring_page(conn,tx,rec)
        elif page=="Transactions":transaction_page(conn,tx)
        elif page=="Bills & renewals":bills_page(conn,rec)
        elif page=="Budget studio":budgets_page(conn,tx,budgets)
        elif page=="Goals & decisions":goals_page(conn,rec,goals)
        elif page=="Ask KeepMore":ai_page(conn,tx,rec,goals,acts)
        elif page=="Settings":settings_page(conn,tx,rec,acts,budgets,goals)

if __name__=="__main__":
    main()
