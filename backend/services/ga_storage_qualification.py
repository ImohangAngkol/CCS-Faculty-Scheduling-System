"""Read-only qualification of owned fixture storage; no deployment activator."""
from dataclasses import dataclass
import base64
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from services.ga_run_authority import RunError
from services.ga_owned_store import CONTRACT,Store

VERSION='ga-deployment-storage-qualification-v1'
REQUIRED=('durable_location','service_account_permissions','atomic_recovery','backup_restore',
    'retention_disposal','physical_disk_quota','owner_isolation','concurrent_access','schema_compatibility','restart_supervision')

@dataclass(frozen=True)
class DeploymentEvidence:
    """References are evidence requests, never self-authorizing approval flags."""
    references:tuple[tuple[str,str],...]=()

def permissions(root):
    root=Path(root)
    if root.parent.resolve()!=Path(tempfile.gettempdir()).resolve() or not root.name.startswith('ga-u5i-'):
        raise RunError('GA_STORAGE_PERMISSION_SCOPE_INVALID')
    if os.name!='nt':
        if root.stat().st_mode&0o077:raise RunError('GA_STORAGE_PERMISSIONS_UNVERIFIED')
        return
    path=str(root).replace("'","''")
    script="""$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
$a=Get-Acl -LiteralPath 'TARGET'
$ids=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
$rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if(-not $a.AreAccessRulesProtected -or $rules.Count -ne 3){throw 'ACL'}
foreach($r in $rules){if($r.IdentityReference.Value -notin $ids -or $r.IsInherited -or $r.AccessControlType -ne 'Allow' -or ($r.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne [Security.AccessControl.FileSystemRights]::FullControl){throw 'ACL'}}
Write-Output 'ACL_VERIFIED'
""".replace('TARGET',path)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],
            env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,text=True,timeout=30)
        if result.returncode or result.stdout.strip()!='ACL_VERIFIED':raise ValueError()
    except Exception:raise RunError('GA_STORAGE_PERMISSIONS_UNVERIFIED',503) from None

def inspect(store,evidence=DeploymentEvidence(),*,minimum_free_bytes=64*1024*1024):
    if type(store) is not Store or type(minimum_free_bytes) is not int or minimum_free_bytes<=0:
        raise RunError('GA_STORAGE_INSPECTION_INVALID')
    store.guard()
    permissions(store.root)
    with store.connection() as db:
        db.execute('BEGIN')
        try:
            integrity=db.execute('PRAGMA quick_check').fetchall()
            if [r[0] for r in integrity]!=['ok'] or db.execute('PRAGMA foreign_key_check').fetchall():
                raise RunError('GA_STORAGE_CORRUPT')
            runs=db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
            checkpoints=db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]
            for row in db.execute('SELECT * FROM runs WHERE tip IS NOT NULL').fetchall():
                store.load_checkpoint(db,dict(row))
        finally:db.rollback()
    refs=dict(evidence.references)
    if len(refs)!=len(evidence.references) or not set(refs)<=set(REQUIRED):raise RunError('GA_STORAGE_EVIDENCE_INVALID')
    # Supplied reference labels alone never qualify actual deployment evidence.
    return {'contract':VERSION,'store_contract':CONTRACT,'scope':'OWNED_OS_TEMP_ONLY',
        'technical_integrity':'PASS','permissions_verified':True,'run_count':runs,'checkpoint_count':checkpoints,
        'minimum_free_space_observed':shutil.disk_usage(store.root).free>=minimum_free_bytes,
        'production_ready':False,'admission_enabled':False,'cleanup_performed':False,
        'deployment_requirements':[{'requirement':key,'reference_supplied':bool(refs.get(key)),
            'status':'INDEPENDENT_DEPLOYMENT_EVIDENCE_REQUIRED'} for key in REQUIRED],
        'blockers':['DURABLE_LOCATION_NOT_CONFIGURED','DEPLOYMENT_POLICY_NOT_APPROVED','PHYSICAL_QUOTA_NOT_ENFORCED',
                    'RESTORE_FENCING_AND_RETENTION_POLICY_REQUIRED']}
