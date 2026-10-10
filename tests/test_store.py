from datetime import date
from pathlib import Path
from keepmore.demo import seed
from keepmore.store import (db,add_transaction,add_recurring,get_setting,setting,
  rows,actions_savings,clear_workspace,add_goal)
from keepmore.engine import opportunities

def test_database_create_persist_export_and_clear(tmp_path):
    dbfile=tmp_path/'keepmore_personal.sqlite3'
    with db(dbfile) as conn:
        add_transaction(conn,'2026-10-01','Groceries','Groceries',-2550)
        add_recurring(conn,'My internet','Utilities',7999,'Monthly','2026-10-20','Not using')
        add_goal(conn,'Emergency savings',500000,15000,'2027-10-01')
        setting(conn,'display_name','Test person')
    with db(dbfile) as conn:
        assert len(rows(conn,'SELECT * FROM transactions'))==1
        assert get_setting(conn,'display_name')=='Test person'
        assert opportunities(rows(conn,'SELECT * FROM recurring'),rows(conn,'SELECT * FROM transactions'))[0]['annual_cents']==7999*12
        clear_workspace(conn)
    with db(dbfile) as conn:
        assert not rows(conn,'SELECT * FROM transactions')
        assert not rows(conn,'SELECT * FROM recurring')
        assert get_setting(conn,'display_name')==''

def test_demo_seed_deterministic_and_idempotent(tmp_path):
    dbfile=tmp_path/'demo.sqlite3'
    with db(dbfile) as conn:
        seed(conn,date(2026,10,10))
        a=rows(conn,'SELECT * FROM transactions');b=rows(conn,'SELECT * FROM recurring')
        seed(conn,date(2026,10,10))
        assert len(a)==len(rows(conn,'SELECT * FROM transactions'))
        assert len(b)==len(rows(conn,'SELECT * FROM recurring'))
        assert len(b)==10
        assert len(a)>=100
        assert get_setting(conn,'display_name')=='Alex'

def test_action_savings_only_completed():
    items=[{"before_cents":5000,"after_cents":3000,"cycle":"Monthly","status":"completed"},
           {"before_cents":10000,"after_cents":0,"cycle":"Monthly","status":"planned"}]
    assert actions_savings(items)==24000
