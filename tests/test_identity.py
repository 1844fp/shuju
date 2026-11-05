import os,sys,tempfile,unittest
from pathlib import Path
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'backend'));sys.path.insert(0,str(r))
import app,identity
from fastapi.testclient import TestClient
class IdentityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();app.app.state.db=app.engine('sqlite:///'+str(Path(self.tmp.name)/'control.db'));app.app.state.tenant_root=Path(self.tmp.name)/'tenants';os.environ['FINAGENT_AUTH_MODE']='users'
  self.a=identity.create_org('A');self.b=identity.create_org('B')
  identity.create_user('admin-a','Test-password-123',self.a['id'],'org_admin');identity.create_user('admin-b','Test-password-123',self.b['id'],'org_admin');identity.create_user('reader-a','Test-password-123',self.a['id'],'reader')
  self.client=TestClient(app.app)
 def tearDown(self):
  self.client.close();os.environ.pop('FINAGENT_AUTH_MODE',None)
  for key,e in list(identity.engines.items()):
   if key.startswith(str(Path(self.tmp.name))):e.dispose();identity.engines.pop(key)
  app.app.state.db.dispose();del app.app.state.tenant_root;self.tmp.cleanup()
 def login(self,name):
  res=self.client.post('/api/v1/auth/login',json={'username':name,'password':'Test-password-123'});self.assertEqual(res.status_code,200,res.text);return res
 def test_sessions_and_logout(self):
  self.assertEqual(self.client.get('/api/v1/imports').status_code,401);r=self.login('admin-a');self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertEqual(self.client.get('/api/v1/auth/me').json()['organization_id'],self.a['id']);self.client.post('/api/v1/auth/logout');self.assertEqual(self.client.get('/api/v1/imports').status_code,401)
 def test_cross_organization(self):
  self.login('admin-a');data=(r/'data_platform/sample_vouchers.csv').read_bytes();preview=self.client.post('/api/v1/imports/preview',files={'file':('sample.csv',data)}).json();batch=self.client.post('/api/v1/imports',json={'preview_id':preview['preview_id']}).json();self.assertEqual(batch['accepted_rows'],72)
  self.login('admin-b');self.assertEqual(self.client.get('/api/v1/metrics/finance').json(),[]);self.assertEqual(self.client.get('/api/v1/imports/'+batch['batch_id']).status_code,404);self.assertEqual(self.client.post('/api/v1/imports',json={'preview_id':preview['preview_id']}).status_code,404)
  self.assertEqual(self.client.get('/api/v1/imports?organization_id='+self.a['id']).status_code,403)
 def test_roles_and_admin(self):
  self.login('reader-a');self.assertEqual(self.client.post('/api/v1/reports',json={}).status_code,403);self.assertEqual(self.client.get('/api/v1/admin/users').status_code,403)
  self.login('admin-a');self.assertEqual(self.client.post('/api/v1/admin/users',json={'username':'escape','password':'Test-password-123','organization_id':self.b['id']}).status_code,403)
  self.assertEqual(self.client.post('/api/v1/admin/users',json={'username':'superadmin','password':'Test-password-123','role':'platform_admin'}).status_code,403)
  self.assertEqual(self.client.post('/api/v1/admin/users',json={'username':'new-reader','password':'Test-password-123'}).status_code,201)
 def test_password_rotation_revokes_sessions(self):
  self.login('admin-a')
  response=self.client.post('/api/v1/auth/password',json={'current_password':'Test-password-123','new_password':'Changed-password-456'})
  self.assertEqual(response.status_code,200,response.text);self.assertEqual(self.client.get('/api/v1/auth/me').status_code,401)
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'username':'admin-a','password':'Changed-password-456'}).status_code,200)
 def test_disable_revokes_sessions(self):
  self.login('reader-a');reader_cookie=self.client.cookies.get('finagent_session');self.login('admin-a')
  records=self.client.get('/api/v1/admin/users').json();reader=next(x for x in records if x['username']=='reader-a')
  self.assertEqual(self.client.patch('/api/v1/admin/users/'+reader['id'],json={'role':'reader','enabled':False}).status_code,200)
  other=TestClient(app.app);other.cookies.set('finagent_session',reader_cookie)
  try:self.assertEqual(other.get('/api/v1/metrics/finance').status_code,401)
  finally:other.close()
 def test_lockout_and_storage(self):
  for _ in range(5):self.assertEqual(self.client.post('/api/v1/auth/login',json={'username':'admin-a','password':'wrong'}).status_code,401)
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'username':'admin-a','password':'Test-password-123'}).status_code,401)
  with identity.ctl().connect() as c:
   row=c.execute(identity.users.select()).mappings().first();self.assertNotIn('Test-password',row['password_hash'])
if __name__=='__main__':unittest.main(verbosity=2)
