"""Independent source-control comparison; never equates self-consistency with completeness."""
from decimal import Decimal
import re
from .theme_imports import BASE,SCHEMAS,value

def observe(parsed):
 theme=parsed['theme'];schema={**BASE,**SCHEMAS[theme]}
 fields=[k for k,v in schema.items() if v in ('money','signed')]
 totals={};keys=set();issues=[]
 rows=parsed['accepted']+parsed['quarantined']
 for row in rows:
  raw=row['original_payload'];key=(raw.get('external_id') or '').strip()
  if key:keys.add(key)
  else:issues.append({'source_row':row['source_row'],'field':'external_id'})
  try:currency=value(raw.get('currency') or '', 'currency')
  except ValueError:issues.append({'source_row':row['source_row'],'field':'currency'});continue
  total=totals.setdefault(currency,{f:Decimal(0) for f in fields})
  for field in fields:
   try:total[field]+=Decimal(value(raw.get(field) or '',schema[field]))
   except ValueError:issues.append({'source_row':row['source_row'],'field':field})
 return {'source_sha256':parsed['source']['sha256'],'row_count':len(rows),'business_key_count':len(keys),'currency_totals':{c:{f:format(n,'.2f') for f,n in t.items()} for c,t in sorted(totals.items())}},issues

def reconcile(parsed,manifest=None):
 observed,issues=observe(parsed)
 result={'status':'not_assessed','observed':observed,'differences':[],'issues':issues,'limitations':['Matched controls do not prove external source completeness or manifest authenticity.']}
 if manifest is None:result['reason']='source_manifest_missing';return result
 required={'version','organization_id','theme','source_sha256','row_count','business_key_count','currency_totals'}
 if set(manifest)!=required or manifest['version']!='source-control-v1':raise ValueError('invalid_manifest_schema')
 if not isinstance(manifest['source_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',manifest['source_sha256']):raise ValueError('invalid_manifest_hash')
 for key in ('row_count','business_key_count'):
  if type(manifest[key]) is not int or manifest[key]<0:raise ValueError('invalid_manifest_count')
 fields={k for k,v in SCHEMAS[parsed['theme']].items() if v in ('money','signed')}
 if not isinstance(manifest['currency_totals'],dict):raise ValueError('invalid_manifest_totals')
 for currency,totals in manifest['currency_totals'].items():
  value(currency,'currency')
  if not isinstance(totals,dict) or set(totals)!=fields:raise ValueError('invalid_manifest_amount_fields')
  for amount in totals.values():
   if not isinstance(amount,str) or not re.fullmatch(r'-?\d+\.\d{2}',amount) or not Decimal(amount).is_finite():raise ValueError('invalid_manifest_amount')
 for key,actual in {'organization_id':parsed['organization_id'],'theme':parsed['theme'],**observed}.items():
  expected=manifest[key]
  if expected!=actual:result['differences'].append({'field':key,'expected':expected,'observed':actual})
 if issues:result['reason']='invalid_source_control_fields';return result
 result['status']='mismatched' if result['differences'] else 'matched'
 return result
