"""Verified SQLite bundles. Restore to a new directory; never overwrite live data."""
import argparse, hashlib, json, os, re, sqlite3, tempfile, time
from contextlib import closing
from pathlib import Path
from infrastructure.backup import copy_database

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def safe_entry(root,name):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}\.sqlite',name):raise ValueError('invalid snapshot filename')
    path=root/name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):raise ValueError('snapshot path escape')
    return path

def verify(bundle):
    bundle=Path(bundle).resolve()
    manifest=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format')!='finagent-sqlite-bundle-v1' or not manifest.get('databases'):raise ValueError('invalid bundle manifest')
    names=[]
    for record in manifest['databases']:
        name=record['file']; path=safe_entry(bundle,name)
        if name in names:raise ValueError('duplicate snapshot entry')
        names.append(name)
        if not path.is_file() or path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:raise ValueError('snapshot checksum mismatch')
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('invalid SQLite snapshot')
    return manifest

def snapshot(databases,destination,*,quiesced=False):
    destination=Path(destination)
    if destination.exists():raise ValueError('destination exists; refusing overwrite')
    if not databases:raise ValueError('no databases specified')
    if len(databases)>1 and not quiesced:raise ValueError('multi-database bundle requires coordinated write pause')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Staging is deliberately retained on failure as diagnostic evidence.
    stage=Path(tempfile.mkdtemp(prefix='snapshot-pending-',dir=destination.parent))
    entries=[]; start=time.monotonic()
    for label,source in sorted(databases.items()):
        target=safe_entry(stage,label+'.sqlite')
        if Path(source).is_symlink():raise ValueError('symlink database source rejected')
        copy_database(Path(source),target)
        entries.append(dict(file=target.name,bytes=target.stat().st_size,sha256=digest(target)))
    manifest=dict(format='finagent-sqlite-bundle-v1',created_unix=time.time(),write_pause_asserted=quiesced,databases=entries,duration_seconds=time.monotonic()-start,scope='SQLite databases only; model weights, .env and PostgreSQL require separate procedures')
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    verify(stage)
    stage.rename(destination)
    return manifest

def restore(bundle,destination):
    manifest=verify(bundle); destination=Path(destination)
    if destination.exists():raise ValueError('destination exists; refusing overwrite')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='restore-pending-',dir=destination.parent)); start=time.monotonic()
    for entry in manifest['databases']:
        source=safe_entry(Path(bundle).resolve(),entry['file']); target=safe_entry(stage,entry['file'])
        # Copy bytes from verified immutable snapshots; no SQLite transformation.
        with source.open('rb') as src,target.open('xb') as dst:
            import shutil
            shutil.copyfileobj(src,dst); dst.flush(); os.fsync(dst.fileno())
        if digest(target)!=entry['sha256']:raise ValueError('restore checksum mismatch')
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    verify(stage); stage.rename(destination)
    return dict(databases=len(manifest['databases']),duration_seconds=time.monotonic()-start)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('snapshot');b.add_argument('--database',action='append',required=True,metavar='LABEL=PATH');b.add_argument('--destination',type=Path,required=True);b.add_argument('--quiesced',action='store_true')
    for command in ('verify','restore'):
        x=sub.add_parser(command);x.add_argument('--bundle',type=Path,required=True)
        if command=='restore':x.add_argument('--destination',type=Path,required=True)
    a=p.parse_args()
    if a.command=='snapshot':
        pairs=[x.split('=',1) for x in a.database]
        if any(len(x)!=2 for x in pairs) or len(dict(pairs))!=len(pairs):p.error('unique LABEL=PATH entries required')
        result=snapshot(dict(pairs),a.destination,quiesced=a.quiesced)
    elif a.command=='restore':result=restore(a.bundle,a.destination)
    else:result=verify(a.bundle)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
