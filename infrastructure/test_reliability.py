import json,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from infrastructure.recovery import snapshot,restore,verify
from infrastructure.production.alerts import Monitor

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path('work'));self.root=Path(self.tmp.name)
        self.db=self.root/'source.sqlite'
        with closing(sqlite3.connect(self.db)) as c:c.execute('create table journal(amount text)');c.execute("insert into journal values ('0.30')");c.commit()
    def tearDown(self):self.tmp.cleanup()
    def test_wal_snapshot_restores_committed_value(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('pragma journal_mode=WAL');c.execute("insert into journal values ('999999999999.99')");c.commit()
            snapshot({'tenant':self.db},self.root/'backup')
        restore(self.root/'backup',self.root/'restore')
        with closing(sqlite3.connect(self.root/'restore/tenant.sqlite')) as c:self.assertEqual(c.execute('select amount from journal').fetchall(),[('0.30',),('999999999999.99',)])
    def test_corruption_and_manifest_escape_rejected(self):
        snapshot({'tenant':self.db},self.root/'backup')
        file=self.root/'backup/tenant.sqlite'
        with file.open('r+b') as f:f.seek(50);f.write(b'bad')
        with self.assertRaises(ValueError):restore(self.root/'backup',self.root/'restore')
        self.assertFalse((self.root/'restore').exists())
        manifest=self.root/'backup/manifest.json';value=json.loads(manifest.read_text());value['databases'][0]['file']='../source.sqlite';manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'invalid snapshot filename'):verify(self.root/'backup')
    def test_multi_database_pause_and_existing_target(self):
        with self.assertRaises(ValueError):snapshot({'a':self.db,'b':self.db},self.root/'backup')
        snapshot({'a':self.db,'b':self.db},self.root/'backup',quiesced=True)
        self.assertEqual(len(verify(self.root/'backup')['databases']),2)
        with self.assertRaises(ValueError):restore(self.root/'backup',self.root/'backup')
    def test_alert_transitions_survive_restart(self):
        path=self.root/'state.json';events=self.root/'events.jsonl';m=Monitor(path,events)
        m.tick(False);self.assertFalse(events.exists());m.tick(False)
        m=Monitor(path,events);m.tick(False);m.tick(True);m.tick(True);m.tick(True)
        self.assertEqual([json.loads(x)['kind'] for x in events.read_text().splitlines()],['service_down','service_recovered'])
    def test_pending_delivery_reuses_event_id(self):
        path=self.root/'state.json';events=self.root/'events.jsonl';m=Monitor(path,events,webhook='http://127.0.0.1:1')
        with patch('infrastructure.production.alerts.request_ok',side_effect=OSError('offline')):m.tick(False);self.assertEqual(m.tick(False)['pending'],1)
        event_id=m.state['pending'][0]['event_id'];m=Monitor(path,events,webhook='http://127.0.0.1:1')
        with patch('infrastructure.production.alerts.request_ok',return_value=True) as delivery:
            self.assertEqual(m.tick(False)['pending'],0);self.assertEqual(delivery.call_args.args[1]['event_id'],event_id)

if __name__=='__main__':unittest.main()
