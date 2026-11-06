"""Restore an isolated acceptance database using the real PostgreSQL tools."""
import hashlib,json,os,subprocess,time
from pathlib import Path

def exercise(root,base,secret,alias):
    import psycopg
    from psycopg import sql
    root=Path(root);output=root/'work/acceptance/postgres';output.mkdir(parents=True,exist_ok=True)
    dump=output/('warehouse-'+str(time.time_ns())+'.dump')
    def compat(value):return str(value).replace(str(root),alias)
    def run(name,args):
        proc=subprocess.run([compat(root/'work/postgres-runtime/pgsql/bin'/(name+'.exe')),'-h','127.0.0.1','-p','55439','-U','owner',*map(compat,args)],env={**os.environ,'PGPASSWORD':secret},cwd=alias+'\\',capture_output=True,timeout=90)
        if proc.returncode:raise RuntimeError(name+' failed; credentials and tool output suppressed')
    def connect(database):return psycopg.connect(host='127.0.0.1',port=55439,dbname=database,user='owner',password=secret)
    def inventory(database):
        result={}
        with connect(database) as c:
            tables=c.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('metadata','ods','dim','dwd','dws','ads','identity') ORDER BY 1,2").fetchall()
            for schema,table in tables:
                rows=c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {}.{} t ORDER BY row_to_json(t)::text').format(sql.Identifier(schema),sql.Identifier(table))).fetchall()
                result[schema+'.'+table]=dict(rows=len(rows),sha256=hashlib.sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest())
        with psycopg.connect(host='127.0.0.1',port=55439,dbname=database,user='reader_a',password=secret) as c:
            rows=c.execute('SELECT row_to_json(t)::text FROM ads.finance_dashboard t ORDER BY row_to_json(t)::text').fetchall()
            if len(rows)!=12:raise AssertionError('restored production reader expected 12 dashboard months')
            result['ads.finance_dashboard:reader_a']=dict(rows=len(rows),sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest())
        return result
    expected=inventory('postgres');start=time.monotonic()
    run('pg_dump',['-F','c','-f',dump,'postgres']);backup_seconds=time.monotonic()-start
    run('createdb',['recovery_acceptance']);start=time.monotonic()
    run('pg_restore',['--exit-on-error','--no-owner','--dbname','recovery_acceptance',dump]);restore_seconds=time.monotonic()-start
    actual=inventory('recovery_acceptance')
    if expected!=actual:raise AssertionError('PostgreSQL restored contents differ')
    result=dict(passed=True,backup_seconds=round(backup_seconds,3),restore_seconds=round(restore_seconds,3),dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),tables=expected,scope='fresh database in isolated test cluster; cluster roles already bootstrapped; not PITR or full cluster disaster recovery')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS: real pg_dump/pg_restore, table content hashes and dashboard view match')
    return result
