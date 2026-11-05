"""Run only against an isolated migrated test database."""
import os
import psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as c:
    assert c.execute('select count(*) from dwd.fact_journal_entry').fetchone()[0] == 72
    assert c.execute('select count(*) from dws.monthly_finance').fetchone()[0] == 12
    c.execute('SET LOCAL ROLE finagent_reader')
    assert c.execute('select count(*) from ads.finance_dashboard').fetchone()[0] == 0
    c.execute("select set_config('app.organization_id','demo',true)")
    assert c.execute('select count(*) from ads.finance_dashboard').fetchone()[0] == 12
    try:
        with c.transaction(): c.execute('delete from dwd.fact_journal_entry')
    except psycopg.errors.InsufficientPrivilege: pass
    else: raise AssertionError('reader can write')
    c.execute('RESET ROLE')
    try:
        with c.transaction():
            c.execute("UPDATE dwd.fact_journal_entry SET account_code='UNKNOWN' WHERE id=(SELECT min(id) FROM dwd.fact_journal_entry)")
    except psycopg.errors.ForeignKeyViolation:pass
    else:raise AssertionError('unknown account accepted')
    batch=c.execute('select id from metadata.data_batch limit 1').fetchone()[0]
    try:
        with c.transaction():
            c.execute("INSERT INTO ods.raw_vouchers VALUES('other-organization',%s,9999,'{}'::jsonb)",(batch,))
    except psycopg.errors.ForeignKeyViolation:pass
    else:raise AssertionError('cross-organization batch reference accepted')
    try:
        with c.transaction():
            c.execute('update dwd.fact_journal_entry set debit=debit+0.01 where id=(select min(id) from dwd.fact_journal_entry where debit>0)')
            c.execute('SET CONSTRAINTS ALL IMMEDIATE')
    except psycopg.errors.CheckViolation: pass
    else: raise AssertionError('unbalanced voucher accepted')
print('PASS PostgreSQL row counts, scoped reader, write denial, unknown account, cross-organization FK, deferred balance')
