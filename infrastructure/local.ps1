param([ValidateSet('start','stop')][string]$Action='start',[int]$Port=8011,[string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$state=Join-Path $root 'work/qa-local'
New-Item -ItemType Directory -Force $state | Out-Null
$record=Join-Path $state 'process.json'
$entry=Join-Path $PSScriptRoot 'local_service.py'
if($Action -eq 'stop') {
 if(!(Test-Path $record)){ Write-Output 'No managed process'; exit 0 }
 $saved=Get-Content $record -Raw | ConvertFrom-Json
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($saved.pid)"
 if($proc){
  if($proc.CreationDate.ToUniversalTime().ToString('o') -ne $saved.created -or !$proc.CommandLine.Contains($entry)){throw 'Process identity mismatch; refusing stop'}
  Stop-Process -Id $saved.pid
 }
 Remove-Item -LiteralPath $record
 exit 0
}
if(Test-Path $record){throw 'Managed record exists; run stop first'}
if(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue){throw 'Port occupied; refusing start'}
$arguments='"'+$entry+'" --port '+$Port+' --data "'+$state+'"'
$child=Start-Process $Python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state 'stdout.log') -RedirectStandardError (Join-Path $state 'stderr.log')
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($child.Id)"
@{pid=$child.Id;created=$proc.CreationDate.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content $record
Start-Sleep -Seconds 2
Invoke-RestMethod "http://127.0.0.1:$Port/api/v1/ready"
