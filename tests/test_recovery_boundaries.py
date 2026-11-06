import tempfile,unittest
from pathlib import Path
from fastapi import HTTPException
import app as core,leased_jobs

class RecoveryBoundaryTests(unittest.TestCase):
    def test_new_tenant_unknown_job_is_404(self):
        with tempfile.TemporaryDirectory(dir=Path('work')) as directory:
            db=core.engine('sqlite:///'+str(Path(directory)/'tenant.sqlite'))
            try:
                with self.assertRaises(HTTPException) as raised:leased_jobs.get(db,'new-org','unknown')
                self.assertEqual(raised.exception.status_code,404)
            finally:db.dispose()

if __name__=='__main__':unittest.main()
