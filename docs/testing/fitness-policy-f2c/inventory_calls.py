"""Static source inventory: no application imports or academic-data reads."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
TOKENS=('fitness','score','checkpoint','scoring','best_ever')


class Inventory(ast.NodeVisitor):
    def __init__(self):self.stack=[];self.calls=[];self.comparisons=[];self.definitions=[];self.imports=[]
    def visit_FunctionDef(self,node):
        self.stack.append(node.name)
        if any(x in node.name.lower() for x in TOKENS):self.definitions.append(dict(line=node.lineno,function='.'.join(self.stack)))
        self.generic_visit(node);self.stack.pop()
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_ImportFrom(self,node):
        for name in node.names:
            if any(x in ((node.module or '')+'.'+name.name).lower() for x in TOKENS):
                self.imports.append(dict(line=node.lineno,module=node.module,name=name.name,alias=name.asname))
    def visit_Call(self,node):
        name=ast.unparse(node.func)
        if any(x in name.lower() for x in TOKENS):
            self.calls.append(dict(line=node.lineno,caller='.'.join(self.stack) or '<module>',callee=name))
        self.generic_visit(node)
    def visit_Compare(self,node):
        # Expression text is source-only; literal strings/numbers are omitted.
        names=sorted({n.id for n in ast.walk(node) if isinstance(n,ast.Name)})
        keys=sorted({n.value for n in ast.walk(node) if isinstance(n,ast.Constant) and isinstance(n.value,str)
            and any(x in n.value.lower() for x in TOKENS)})
        if any(any(x in n.lower() for x in TOKENS) for n in names) or keys:
            self.comparisons.append(dict(line=node.lineno,caller='.'.join(self.stack) or '<module>',
                variables=names,keys=keys,operators=[type(op).__name__ for op in node.ops]))
        self.generic_visit(node)


def collect():
    files=[]
    for path in sorted((ROOT/'backend').rglob('*.py')):
        rel=path.relative_to(ROOT).as_posix()
        if any(x in path.parts for x in ('tests','benchmarks','__pycache__')) or path.name=='ga_v2_fictional_python_baseline.py':continue
        source=path.read_bytes();visitor=Inventory();visitor.visit(ast.parse(source))
        if visitor.calls or visitor.imports or visitor.definitions or visitor.comparisons:
            files.append(dict(path=rel,sha256=hashlib.sha256(source).hexdigest(),definitions=visitor.definitions,
                scoring_related_imports=visitor.imports,calls=visitor.calls,comparisons=visitor.comparisons))
    return dict(scope='Static name-based index; curated report explains active paths, storage, observers and alternate scorers. Not dynamic coverage.',files=files)


if __name__=='__main__':
    data=collect()
    with Path(sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
    print(json.dumps(dict(indexed_files=len(data['files']),calls=sum(len(x['calls']) for x in data['files']))))
