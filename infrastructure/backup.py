"""Consistent SQLite snapshot and restore-to-new-file verification; never overwrites."""
import argparse,sqlite3
from contextlib import closing
from pathlib import Path

def copy_database(source:Path,destination:Path):
    if not source.is_file():raise ValueError('Source database does not exist')
    if destination.exists():raise ValueError('Destination exists; refusing overwrite')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)
        if dst.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed')
    print('PASS: consistent database copy with integrity_check=ok:',destination)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();copy_database(a.source,a.destination)
