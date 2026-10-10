"""Clearly fictional data, inserted only into the separate demo workspace."""
from datetime import date, timedelta
from calendar import monthrange
from keepmore.engine import add_months
from keepmore.store import add_recurring, add_transaction, get_setting, setting
import random

def seed(conn,today: date | None=None) -> None:
    today=today or date.today()
    if get_setting(conn,"seeded"):
        return
    rng=random.Random(2026)
    base=today.replace(day=1)
    plans=[
        ("Home rent", "Housing",125000,"Monthly",1,"Essential"),
        ("Metro Electric", "Utilities",15480,"Monthly",12,"Essential"),
        ("Broadband Home", "Utilities",7999,"Monthly",18,"Use it"),
        ("Cellular Family", "Utilities",8640,"Monthly",24,"Use it"),
        ("SafeWay Auto Insurance", "Insurance",13900,"Monthly",9,"Essential"),
        ("StreamNow", "Subscriptions",1999,"Monthly",14,"Use it"),
        ("MusicFlow", "Subscriptions",1299,"Monthly",17,"Use it"),
        ("CloudBox", "Subscriptions",999,"Monthly",25,"Use it"),
        ("FitClub", "Subscriptions",3900,"Monthly",23,"Not using"),
        ("DesignPro", "Subscriptions",2799,"Monthly",28,"Not using"),
    ]
    for name,cat,amount,cycle,day,usage in plans:
        next_date=date(today.year,today.month,min(day,monthrange(today.year,today.month)[1]))
        if next_date<today:
            next_date=add_months(next_date,1,day)
        add_recurring(conn,name,cat,amount,cycle,next_date.isoformat(),usage,"Fictional sample data",origin="demo")
    for i in range(7, -1,-1):
        m=add_months(base,-i)
        for name,cat,amount,cycle,day,usage in plans:
            pay=amount
            if name=="Broadband Home" and i>=2:pay=6999
            if name=="MusicFlow" and i>=2:pay=1099
            if name=="Metro Electric":pay=round(amount*rng.uniform(.85,1.17))
            if name=="Home rent" and i>=2:pay=122500
            on=date(m.year,m.month,min(day,monthrange(m.year,m.month)[1]))
            if on<=today:
                add_transaction(conn,on.isoformat(),name,cat,-pay,source="demo")
        for day in [3,17]:
            on=date(m.year,m.month,day)
            if on<=today:
                add_transaction(conn,on.isoformat(),"Payroll deposit","Other",215000,source="demo")
        extras=[("Green Basket Grocery","Groceries",rng.randint(5200,9300)),("Green Basket Grocery","Groceries",rng.randint(6700,10600)),("Corner Market","Groceries",rng.randint(2600,5300)),("Parkside Coffee","Dining",rng.randint(1100,2600)),("Lunch Spot","Dining",rng.randint(2200,4100)),("Fuel Stop","Transport",rng.randint(3500,5500)),("Fuel Stop","Transport",rng.randint(3200,5400)),("Household Supplies Store","Shopping",rng.randint(3500,9900)),("Family Fun","Family",rng.randint(2500,6700)),("Health Pharmacy","Health",rng.randint(800,3800))]
        for j,(name,cat,amount) in enumerate(extras):
            d=min(2+j*2,monthrange(m.year,m.month)[1])
            on=date(m.year,m.month,d)
            if on<=today:
                add_transaction(conn,on.isoformat(),name,cat,-amount,source="demo")
    for cat,limit in {"Groceries":58000,"Dining":12000,"Transport":20000,"Shopping":18000,"Entertainment":8000,"Family":14000,"Health":10000}.items():
        conn.execute("INSERT INTO budgets(category,limit_cents) VALUES(?,?)",(cat,limit))
    conn.execute("INSERT INTO goals(title,target_cents,saved_cents,target_date) VALUES (?,?,?,?)",("Emergency cushion",300000,82500,add_months(today,10).isoformat()))
    conn.execute("INSERT INTO goals(title,target_cents,saved_cents,target_date) VALUES (?,?,?,?)",("Summer trip",125000,44500,add_months(today,7).isoformat()))
    setting(conn,"monthly_income","430000")
    setting(conn,"display_name","Alex")
    setting(conn,"seeded","1")
