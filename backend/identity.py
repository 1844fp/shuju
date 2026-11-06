"""Session authentication and physical organization database isolation."""
import hashlib,hmac,secrets,json,os,time,re
from pathlib import Path
from threading import RLock
from fastapi import HTTPException,Request,Response
from fastapi.responses import JSONResponse,FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import Table,Column,String,Integer,MetaData,select,update
import app as core
control=MetaData()
organizations=Table('security_organization',control,Column('id',String,primary_key=True),Column('name',String),Column('created_at',String))
users=Table('security_user',control,Column('id',String,primary_key=True),Column('username',String,unique=True),Column('password_hash',String),Column('organization_id',String),Column('role',String),Column('enabled',Integer),Column('failures',Integer),Column('locked_until',Integer))
sessions=Table('security_session',control,Column('digest',String,primary_key=True),Column('user_id',String),Column('expires',Integer))
ROLES={'platform_admin','org_admin','analyst','reader'}
engines={};lock=RLock()
def ctl():
    e=core.app.state.db
    with lock: control.create_all(e)
    return e

def password_hash(value):
    if len(value)<12 or len(value)>200:raise ValueError('密码须包含12至200个字符')
    salt=secrets.token_bytes(16);key=hashlib.scrypt(value.encode(),salt=salt,n=16384,r=8,p=1)
    return salt.hex()+':'+key.hex()
def password_check(value,encoded):
    if len(value)>200:return False
    salt,expected=encoded.split(':');key=hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1)
    return hmac.compare_digest(key.hex(),expected)

def create_org(name):
    if not name.strip() or len(name)>100:raise ValueError('组织名称无效')
    row={'id':core.uid(),'name':name,'created_at':core.now()}
    with ctl().begin() as c:c.execute(organizations.insert().values(**row))
    return row

def create_user(username,password,org_id,role):
    if not re.fullmatch('[A-Za-z0-9_.@-]{3,80}',username):raise ValueError('用户名须为3至80位字母、数字或_.@-')
    if role not in ROLES:raise ValueError('角色无效')
    row=dict(id=core.uid(),username=username,password_hash=password_hash(password),organization_id=org_id,role=role,enabled=1,failures=0,locked_until=0)
    with ctl().begin() as c:
        if not c.execute(select(organizations.c.id).where(organizations.c.id==org_id)).first():raise ValueError('组织不存在')
        if c.execute(select(users.c.id).where(users.c.username==username)).first():raise HTTPException(409,'用户名已存在')
        c.execute(users.insert().values(**row))
    return {k:row[k] for k in ('id','username','organization_id','role')}

def tenant_engine(org_id):
    # Only a server-generated UUID from the authenticated identity is used in a filename.
    import uuid
    safe=str(uuid.UUID(org_id));base=Path(getattr(core.app.state,'tenant_root',core.ROOT/'tenants')).resolve();base.mkdir(parents=True,exist_ok=True)
    path=base/(safe+'.sqlite');key=str(path)
    with lock:
        if key not in engines:
            engines[key]=core.engine('sqlite:///'+str(path))
            import jobs
            jobs.recover(engines[key])
        return engines[key]

def authenticate(request):
    supplied=request.cookies.get('finagent_session','')
    if request.headers.get('authorization','').startswith('Bearer '):supplied=request.headers['authorization'][7:]
    if not supplied:return None
    digest=hashlib.sha256(supplied.encode()).hexdigest()
    with ctl().connect() as c:
        s=c.execute(select(sessions).where(sessions.c.digest==digest,sessions.c.expires>int(time.time()))).mappings().first()
        if not s:return None
        u=c.execute(select(users).where(users.c.id==s['user_id'],users.c.enabled==1)).mappings().first()
    return dict(u) if u else None

def public_user(u):return {**{k:u[k] for k in ('id','username','organization_id','role')},'enabled':bool(u['enabled'])}
class Login(BaseModel):
    username:str=Field(min_length=3,max_length=80)
    password:str=Field(min_length=1,max_length=200)
class NewUser(BaseModel):
    username:str
    password:str=Field(min_length=12,max_length=200)
    role:str='reader'
    organization_id:str|None=None
class NewOrg(BaseModel):name:str=Field(min_length=1,max_length=100)
class UserUpdate(BaseModel):
    role:str
    enabled:bool=True
class PasswordChange(BaseModel):
    current_password:str=Field(min_length=1,max_length=200)
    new_password:str=Field(min_length=12,max_length=200)

def install_identity(app):
    @app.middleware('http')
    async def organization_scope(request,call_next):
        if os.getenv('FINAGENT_AUTH_MODE','demo')!='users':return await call_next(request)
        path=request.url.path
        public=path in ('/api/v1/health','/api/v1/ready','/api/v1/auth/login','/api/v1/auth/status')
        if not path.startswith('/api/v1/') or public:return await call_next(request)
        u=authenticate(request)
        if not u:return JSONResponse(status_code=401,content={'error':{'code':'unauthorized','message':'请登录','trace_id':core.uid()}})
        request.state.identity=u
        if request.method not in ('GET','HEAD','OPTIONS') and not path.startswith('/api/v1/auth/'):
            allowed=u['role'] in ('org_admin','platform_admin') or (u['role']=='analyst' and (path.startswith('/api/v1/analysis') or path.startswith('/api/v1/reports') or path.startswith('/api/v1/jobs') or path.startswith('/api/v1/durable-jobs')))
            if not allowed:return JSONResponse(status_code=403,content={'error':{'code':'forbidden','message':'当前角色无权执行此操作','trace_id':core.uid()}})
        organization_marker=core.request_organization.set(u['organization_id'])
        marker=core.request_database.set(tenant_engine(u['organization_id']))
        actor_marker=core.request_actor.set({k:u[k] for k in ('id','username','role','organization_id')})
        try:return await call_next(request)
        finally:
            core.request_actor.reset(actor_marker)
            core.request_database.reset(marker)
            core.request_organization.reset(organization_marker)

    @app.get('/login')
    def login_page():return FileResponse(core.ROOT/'frontend'/'login.html')
    @app.get('/api/v1/auth/status')
    def auth_status():return {'mode':os.getenv('FINAGENT_AUTH_MODE','demo'),'bootstrap':'使用backend/admin.py在终端初始化管理员；无默认密码'}
    @app.post('/api/v1/auth/login')
    def login(body:Login,response:Response):
        if os.getenv('FINAGENT_AUTH_MODE','demo')!='users':raise HTTPException(409,'用户模式未启用')
        with ctl().begin() as c:
            u=c.execute(select(users).where(users.c.username==body.username)).mappings().first()
            valid=False
            if u and u['enabled'] and u['locked_until']<=int(time.time()):valid=password_check(body.password,u['password_hash'])
            else:password_check(body.password,'00'*16+':'+'00'*64)
            if not valid:
                if u:
                    failures=u['failures']+1;c.execute(update(users).where(users.c.id==u['id']).values(failures=failures,locked_until=int(time.time())+900 if failures>=5 else u['locked_until']))
            else:
                c.execute(update(users).where(users.c.id==u['id']).values(failures=0,locked_until=0))
                value=secrets.token_urlsafe(48);c.execute(sessions.insert().values(digest=hashlib.sha256(value.encode()).hexdigest(),user_id=u['id'],expires=int(time.time())+28800))
        if not valid:raise HTTPException(401,'用户名或密码无效，或账户暂时锁定')
        response.set_cookie('finagent_session',value,max_age=28800,httponly=True,samesite='strict',secure=os.getenv('FINAGENT_COOKIE_SECURE')=='1',path='/')
        return public_user(u)
    @app.post('/api/v1/auth/logout')
    def logout(request:Request,response:Response):
        value=request.cookies.get('finagent_session','')
        if request.headers.get('authorization','').startswith('Bearer '):value=request.headers['authorization'][7:]
        with ctl().begin() as c:c.execute(sessions.delete().where(sessions.c.digest==hashlib.sha256(value.encode()).hexdigest()))
        response.delete_cookie('finagent_session',path='/');return {'status':'logged_out'}
    @app.get('/api/v1/auth/me')
    def me(request:Request):
        if os.getenv('FINAGENT_AUTH_MODE','demo')!='users':return {'role':'demo','organization_id':'local-demo'}
        return public_user(request.state.identity)
    @app.post('/api/v1/admin/organizations',status_code=201)
    def organization(body:NewOrg,request:Request):
        u=getattr(request.state,'identity',{})
        if u.get('role')!='platform_admin':raise HTTPException(403,'仅平台管理员可创建组织')
        return create_org(body.name)
    @app.post('/api/v1/admin/users',status_code=201)
    def new_user(body:NewUser,request:Request):
        u=getattr(request.state,'identity',{})
        if u.get('role') not in ('platform_admin','org_admin'):raise HTTPException(403,'需要管理员权限')
        org=body.organization_id or u['organization_id']
        if u['role']!='platform_admin' and (org!=u['organization_id'] or body.role=='platform_admin'):raise HTTPException(403,'不可跨组织或授予平台管理员')
        return create_user(body.username,body.password,org,body.role)
    @app.get('/api/v1/admin/users')
    def list_users(request:Request):
        u=getattr(request.state,'identity',{})
        if u.get('role') not in ('platform_admin','org_admin'):raise HTTPException(403,'需要管理员权限')
        with ctl().connect() as c:
            query=select(users)
            if u['role']!='platform_admin':query=query.where(users.c.organization_id==u['organization_id'])
            return [public_user(x) for x in c.execute(query).mappings()]

    @app.patch('/api/v1/admin/users/{user_id}')
    def update_user(user_id:str,body:UserUpdate,request:Request):
        actor=getattr(request.state,'identity',{})
        if actor.get('role') not in ('platform_admin','org_admin'):raise HTTPException(403,'需要管理员权限')
        if body.role not in ROLES:raise ValueError('角色无效')
        with ctl().begin() as c:
            target=c.execute(select(users).where(users.c.id==user_id)).mappings().first()
            if not target:raise HTTPException(404,'用户不存在')
            if actor['role']!='platform_admin' and (target['organization_id']!=actor['organization_id'] or target['role']=='platform_admin' or body.role=='platform_admin'):raise HTTPException(403,'不可修改组织外用户或平台管理员')
            if user_id==actor['id'] and (not body.enabled or body.role!=actor['role']):raise HTTPException(409,'不可禁用自己或改变自己的管理员角色')
            c.execute(update(users).where(users.c.id==user_id).values(role=body.role,enabled=int(body.enabled)))
            c.execute(sessions.delete().where(sessions.c.user_id==user_id))
        return {'id':user_id,'role':body.role,'enabled':body.enabled,'sessions_revoked':True}

    @app.post('/api/v1/auth/password')
    def change_password(body:PasswordChange,request:Request,response:Response):
        actor=getattr(request.state,'identity',None)
        if not actor:raise HTTPException(401,'请登录')
        if not password_check(body.current_password,actor['password_hash']):raise HTTPException(401,'当前密码无效')
        encoded=password_hash(body.new_password)
        with ctl().begin() as c:
            c.execute(update(users).where(users.c.id==actor['id']).values(password_hash=encoded,failures=0,locked_until=0))
            c.execute(sessions.delete().where(sessions.c.user_id==actor['id']))
        response.delete_cookie('finagent_session',path='/')
        return {'status':'password_changed','sessions_revoked':True}

    @app.get('/api/v1/admin/organizations')
    def list_organizations(request:Request):
        actor=getattr(request.state,'identity',{})
        if actor.get('role')!='platform_admin':raise HTTPException(403,'需要平台管理员权限')
        with ctl().connect() as c:return [dict(x) for x in c.execute(select(organizations)).mappings()]
