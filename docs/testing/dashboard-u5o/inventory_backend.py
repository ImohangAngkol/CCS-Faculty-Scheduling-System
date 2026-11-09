"""Static production service/model/migration/storage map; no app/data imports."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent

def main():
    services=[];persistence=[];models=[];migrations=[]
    for folder in ['backend/services','backend/routers','backend/genetic_algorithm']:
        for p in sorted((ROOT/folder).rglob('*.py')):
            text=p.read_text(encoding='utf-8-sig');tree=ast.parse(text);rel=p.relative_to(ROOT).as_posix()
            imports=[];functions=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
                if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    functions.append(dict(name=n.name,line=n.lineno,calls=sorted({ast.unparse(c.func) for c in ast.walk(n) if isinstance(c,ast.Call)})))
                if isinstance(n,ast.Assign):
                    for target in n.targets:
                        if isinstance(target,ast.Name) and re.search(r'(?:_DIR|_FILE|_PATH|MAX_(?:BYTES|LINES|RUNS)|CHECKPOINT|SNAPSHOT)',target.id):
                            expr=ast.unparse(n.value)
                            if '://' not in expr:persistence.append(dict(file=rel,line=n.lineno,symbol=target.id,expression=expr[:350],verification='STATIC_CONFIGURATION_ONLY'))
            services.append(dict(file=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),imports=sorted(set(imports)),functions=functions))
    for p in sorted((ROOT/'backend').glob('*models.py')):
        tree=ast.parse(p.read_text(encoding='utf-8-sig'));tables=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__tablename__' for t in node.targets) and isinstance(node.value,ast.Constant):tables.append(node.value.value)
        models.append(dict(file=p.relative_to(ROOT).as_posix(),tables=tables,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for p in sorted((ROOT/'backend/migrations/versions').glob('*.py')):
        tree=ast.parse(p.read_text(encoding='utf-8-sig'));ids={}
        for n in tree.body:
            if isinstance(n,ast.Assign):
                for target in n.targets:
                    if isinstance(target,ast.Name) and target.id in {'revision','down_revision'}:ids[target.id]=ast.literal_eval(n.value)
        migrations.append(dict(file=p.relative_to(ROOT).as_posix(),**ids,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),execution='NOT_RUN'))
    db=ast.parse((ROOT/'backend/database.py').read_text(encoding='utf-8-sig'))
    env_names=sorted({n.args[0].value for n in ast.walk(db) if isinstance(n,ast.Call) and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) and n.args[0].value.isupper()})
    taskfile=ROOT/'.vscode/tasks.json';tasks=json.loads(taskfile.read_text(encoding='utf-8'))
    taskrows=[dict(label=t.get('label'),type=t.get('type'),command=t.get('command'),dependsOn=t.get('dependsOn'),environment_keys=list(t.get('options',{}).get('env',{})),scope='DEVELOPMENT_TASK_NOT_SEVEN_DAY_SUPERVISOR') for t in tasks.get('tasks',[])]
    result=dict(scope='Static source only; no academic rows, environment values, notebook outputs or databases read',modules=services,persistence_symbols=persistence,models=models,migrations=migrations,database_environment_names=env_names,developer_tasks=taskrows,
        scheduler_references=[dict(file=s['file'],functions=[f['name'] for f in s['functions'] if re.search(r'schedul|worker|heartbeat|deadline',f['name'])]) for s in services if any(re.search(r'schedul|worker|heartbeat|deadline',f['name']) for f in s['functions'])],
        notebook_paths=[p.relative_to(ROOT).as_posix() for p in (ROOT/'backend').rglob('*.ipynb')],notebook_runtime='No notebook execution mechanism is inferred from notebook presence; runtime imports mapped separately')
    with (BASE/'backend-static-inventory.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='STATIC_BACKEND_INVENTORY_CREATED',modules=len(services),functions=sum(len(s['functions']) for s in services),persistence_symbols=len(persistence),model_files=len(models),migration_files=len(migrations),development_tasks=len(taskrows))))

if __name__=='__main__':main()
