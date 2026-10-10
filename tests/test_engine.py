from datetime import date
import io
import pytest
from keepmore.engine import (cents,money,add_months,next_due,normalize_merchant,
    detect_recurring,detect_price_increase,opportunities,monthly_equivalent,parse_csv,category_spend, calendar_ics)

def test_money_parser_and_rounding():
    assert cents("($1,234.55)")==-123455
    assert cents("0.005")==1
    assert cents("-19.99")==-1999
    assert money(-1999)=="−$19.99"
    for wrong in ("abc", "", "NaN", "Infinity"):
        with pytest.raises(ValueError):cents(wrong)

def test_due_dates_and_month_boundaries():
    assert add_months(date(2026,1,31),1)==date(2026,2,28)
    assert next_due(date(2026,1,31),"Monthly",date(2026,3,2))==date(2026,3,31)
    assert next_due(date(2026,9,30),"Weekly",date(2026,10,10))==date(2026,10,14)
    assert next_due(date(2025,12,31),"Yearly",date(2026,10,10))==date(2026,12,31)

def test_recurring_detection_and_existing_exclusion():
    today=date(2026,10,10)
    tx=[{"occurred_on":f"2026-{m:02d}-05","merchant":"ACME Music 002344 POS","amount_cents":-1299,"category":"Subscriptions"} for m in range(5,11)]
    found=detect_recurring(tx,[],today)
    assert len(found)==1
    assert found[0]["cycle"]=="Monthly"
    assert found[0]["next_due"]=="2026-11-05"
    assert found[0]["confidence"]=="High"
    assert not detect_recurring(tx,[{"merchant":"ACME Music", "status":"active"}],today)

def test_irregular_spend_is_not_subscription():
    tx=[{"occurred_on":d,"merchant":"Random Shopping","amount_cents":-p,"category":"Shopping"} for d,p in zip(["2026-09-01","2026-09-04","2026-09-29","2026-10-06"],[1050,5030,1020,9000])]
    assert not detect_recurring(tx,[],date(2026,10,10))

def test_price_increase_and_opportunity_sources():
    tx=[{"occurred_on":f"2026-{m:02d}-10","merchant":"Internet Plan","amount_cents":-old,"category":"Utilities"} for m,old in [(5,6900),(6,6900),(7,6900),(8,6900),(9,7900)]]
    assert detect_price_increase("Internet Plan",tx,7900)["increase_cents"]==1000
    rec=[{"id":1,"merchant":"Internet Plan","amount_cents":7900,"cycle":"Monthly","usage":"Use it","status":"active"}]
    assert sum(x['annual_cents'] for x in opportunities(rec,tx))==12000
    rec[0]['usage']='Not using'
    opps=opportunities(rec,tx)
    assert sum(x['annual_cents'] for x in opps)==7900*12  # no double counted increase

def test_csv_import_signs_and_errors():
    raw=b"Date,Description,Amount\n2026-10-01,Grocery Store,-50.12\n2026-10-02,Salary,2000.00\ninvalid,Gym,-19.99\n"
    mapping={"date":"Date","description":"Description","amount":"Amount"}
    imported,errors=parse_csv(raw,mapping)
    assert len(imported)==2 and len(errors)==1
    assert imported[0]['amount_cents']==-5012
    assert imported[1]['amount_cents']==200000
    inverted,errors=parse_csv(raw,mapping,sign_mode='positive')
    assert inverted[0]['amount_cents']==5012
    assert inverted[1]['amount_cents']==-200000
    debit_credit=b"date,payee,debit,credit\n2026-10-01,Rent,1250,\n2026-10-02,Paycheck,,2300\n"
    result,issues=parse_csv(debit_credit,{"date":"date","description":"payee","debit":"debit","credit":"credit"})
    assert not issues and [x['amount_cents'] for x in result]==[-125000,230000]

def test_weekly_monthly_equivalent_and_calendar():
    assert monthly_equivalent(10000,"Weekly") == (10000*52/12)
    ics=calendar_ics([{"id":1,"merchant":"Test & Family Plan","amount_cents":1999,"cycle":"Monthly","next_due":"2026-11-01","status":"active"}]).decode()
    assert "BEGIN:VCALENDAR" in ics and "END:VEVENT" in ics and "Bill due" in ics
