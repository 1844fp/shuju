"""Local interactive bootstrap. No default password or public bootstrap endpoint."""
import getpass,argparse
import run
from identity import create_org,create_user,ctl,users
from sqlalchemy import select
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--username',default='admin');p.add_argument('--organization',default='默认组织');a=p.parse_args()
with ctl().connect() as c:
    if c.execute(select(users.c.id)).first():raise SystemExit('已存在用户，请通过管理员接口管理；不重复初始化')
pw=getpass.getpass('管理员密码（至少12字符）：')
if pw!=getpass.getpass('再次输入密码：'):raise SystemExit('密码不一致')
org=create_org(a.organization);u=create_user(a.username,pw,org['id'],'platform_admin')
print('已初始化：',u['username'],'组织：',org['id'])
print('设置FINAGENT_AUTH_MODE=users后重启后端，访问/login登录。新组织数据库默认无演示数据。')
