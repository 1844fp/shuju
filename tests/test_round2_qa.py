import sys,unittest,tempfile,sqlite3
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from infrastructure.backup import copy_database
class BackupTests(unittest.TestCase):
 def test_roundtrip_and_refuse_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp:
   a,b,c=[Path(tmp)/x for x in ('source.db','backup.db','restore.db')]
   with closing(sqlite3.connect(a)) as db:
    db.execute('create table evidence(amount text)');db.execute("insert into evidence values ('0.30')");db.commit()
   copy_database(a,b);copy_database(b,c)
   with closing(sqlite3.connect(c)) as db:self.assertEqual(db.execute('select amount from evidence').fetchone()[0],'0.30')
   with self.assertRaises(ValueError):copy_database(b,c)
if __name__=='__main__':unittest.main(verbosity=2)
