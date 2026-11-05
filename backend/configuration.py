"""Local configuration loader: no interpolation, shell execution or secret logging."""
from pathlib import Path
import os,re
ALLOWED_PREFIXES=('FINAGENT_','DATABASE_URL','REDIS_URL','OPENAI_','APP_','HOST','PORT','AUTH_','UPLOAD_','SQL_','POSTGRES_','DBT_','API_BASE_URL')
def load(root):
    path=Path(root)/'.env'
    if not path.is_file():return
    for number,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):continue
        if '=' not in line:raise ValueError(f'.env第{number}行格式无效')
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if not re.fullmatch('[A-Z][A-Z0-9_]*',key) or not key.startswith(ALLOWED_PREFIXES):raise ValueError(f'.env第{number}行变量名不在允许范围')
        if len(value)>=2 and value[0] in ('"',"'") and value[-1]==value[0]:value=value[1:-1]
        os.environ.setdefault(key,value)
