// Static syntax inventory, not evidence that a rendered feature works.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const require=createRequire(path.join(root,'frontend/package.json'));
const ts=require('typescript');
const relative=p=>path.relative(root,p).replaceAll('\\','/');
const walk=p=>fs.readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(p,e.name)):[path.join(p,e.name)]);
const files=walk(path.join(root,'frontend/src')).filter(p=>/\.tsx?$/.test(p));
const sources=new Map(files.map(p=>[relative(p),ts.createSourceFile(p,fs.readFileSync(p,'utf8'),ts.ScriptTarget.Latest,true,p.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS)]));
const imports={},requests=[],features=[],routeNodes=[];
const clean=s=>s.replace(/\s+/g,' ').slice(0,240);
for(const [name,sf] of sources){
  const symbols=new Map();
  function collect(node){if(ts.isVariableDeclaration(node)&&ts.isIdentifier(node.name)&&node.initializer)symbols.set(node.name.text,node.initializer);ts.forEachChild(node,collect);}
  collect(sf);
  function url(node,depth=0){
    if(!node||depth>7)return '{dynamic}';
    if(ts.isStringLiteralLike(node))return node.text;
    if(ts.isIdentifier(node))return symbols.has(node.text)?url(symbols.get(node.text),depth+1):'${'+node.text+'}';
    if(ts.isTemplateExpression(node))return node.head.text+node.templateSpans.map(s=>url(s.expression,depth+1)+s.literal.text).join('');
    if(ts.isBinaryExpression(node)&&node.operatorToken.kind===ts.SyntaxKind.PlusToken)return url(node.left,depth+1)+url(node.right,depth+1);
    if(ts.isCallExpression(node)&&node.expression.getText(sf)==='encodeURIComponent')return url(node.arguments[0],depth+1);
    return '{'+clean(node.getText(sf))+'}';
  }
  imports[name]=[];
  for(const stmt of sf.statements){
    if(ts.isImportDeclaration(stmt)&&ts.isStringLiteral(stmt.moduleSpecifier)){
      const spec=stmt.moduleSpecifier.text;
      if(spec.startsWith('.')){
        const base=path.resolve(path.dirname(sf.fileName),spec.replace(/\.tsx?$/,''));
        const resolved=[base+'.ts',base+'.tsx',path.join(base,'index.ts'),path.join(base,'index.tsx')].find(p=>fs.existsSync(p));
        if(resolved)imports[name].push(relative(resolved));
      }
    }
  }
  function visit(node){
    const line=sf.getLineAndCharacterOfPosition(node.getStart(sf)).line+1;
    if(ts.isCallExpression(node)){
      const callee=node.expression.getText(sf);
      if(/^(?:(?:apiClient|api|client|axios)\.(?:get|post|put|patch|delete|request)|fetch|apiFetch|EventSource|readGAJSON|readGAControlJSON|apiRequest|requestJson)$/.test(callee)){
        const explicit=callee.match(/\.(get|post|put|patch|delete)$/)?.[1]?.toUpperCase();
        const options=node.arguments[1];
        const method=options&&ts.isObjectLiteralExpression(options)?options.properties.find(p=>p.name?.getText(sf)==='method'):undefined;
        requests.push({file:name,line,callee,arguments:node.arguments.map(a=>clean(a.getText(sf))),url_template:url(node.arguments[0]),method:explicit??(method&&ts.isPropertyAssignment(method)&&ts.isStringLiteral(method.initializer)?method.initializer.text:'GET_OR_DYNAMIC_OPTIONS'),verification:'STATIC_ONLY'});
      }
    }
    if(ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node)){
      const tag=node.tagName.getText(sf),attrs={};
      for(const attr of node.attributes.properties){
        if(ts.isJsxAttribute(attr))attrs[attr.name.getText(sf)]=attr.initializer?clean(attr.initializer.getText(sf)):'true';
      }
      const events=Object.fromEntries(Object.entries(attrs).filter(([k])=>/^on[A-Z]/.test(k)));
      const role=attrs.role?.replaceAll('"','');
      const kinds=[];
      if(['button','input','select','textarea','form','a','Link','NavLink','details'].includes(tag))kinds.push(tag);
      if(Object.keys(events).length&&!kinds.length)kinds.push('event-control');
      if(tag==='table')kinds.push('table');
      if(['dialog','alertdialog'].includes(role)||attrs['aria-modal']==='{true}'||/Modal|Dialog/.test(tag))kinds.push('modal');
      if(/^(?:LineChart|BarChart|PieChart|AreaChart|RadarChart|ComposedChart|FullCalendar)$/.test(tag))kinds.push('chart-or-calendar');
      if(kinds.length){
        const owner=ts.isJsxOpeningElement(node)?node.parent:node;
        let enclosing=node.parent;
        while(enclosing&&!ts.isFunctionDeclaration(enclosing)&&!ts.isArrowFunction(enclosing)&&!ts.isFunctionExpression(enclosing))enclosing=enclosing.parent;
        features.push({id:'UI-'+String(features.length+1).padStart(4,'0'),file:name,line,tag,kinds,
          enclosing_function:enclosing?.name?.getText(sf)??(enclosing?.parent&&ts.isVariableDeclaration(enclosing.parent)?enclosing.parent.name.getText(sf):'anonymous_or_module'),
          label:attrs['aria-label']??attrs.title??clean(owner.getText(sf).replace(/<[^>]*>/g,' ')),
          events,attributes:Object.fromEntries(Object.entries(attrs).filter(([k])=>['type','name','id','to','href','disabled','role','aria-modal','value'].includes(k))),
          status:'NOT TESTED',basis:'Static JSX site only; repeated runtime rows count once. Rendering/handler syntax is not end-to-end evidence.'});
      }
      if(tag==='Route')routeNodes.push({file:name,line,attributes:attrs});
    }
    ts.forEachChild(node,visit);
  }
  visit(sf);
}
const sf=sources.get('frontend/src/routes/AppRoutes.tsx');
const routes=[];
function routeVisit(node,parent=''){
  if(ts.isJsxElement(node)&&node.openingElement.tagName.getText(sf)==='Route'){
    const attrs=node.openingElement.attributes.properties;
    const raw=attrs.find(a=>ts.isJsxAttribute(a)&&a.name.getText(sf)==='path')?.initializer;
    const part=raw&&ts.isStringLiteral(raw)?raw.text:'';
    const full=part.startsWith('/')?part:(parent.replace(/\/$/,'')+'/'+part).replace(/\/$/,'')||'/';
    routes.push({path:full,index:attrs.some(a=>a.name?.getText(sf)==='index'),line:sf.getLineAndCharacterOfPosition(node.getStart(sf)).line+1,element:clean(attrs.find(a=>a.name?.getText(sf)==='element')?.initializer?.getText(sf)??''),status:'NOT TESTED'});
    for(const child of node.children)routeVisit(child,full);
    return;
  }
  if(ts.isJsxSelfClosingElement(node)&&node.tagName.getText(sf)==='Route'){
    const attrs=node.attributes.properties;const raw=attrs.find(a=>a.name?.getText(sf)==='path')?.initializer;
    const part=raw&&ts.isStringLiteral(raw)?raw.text:'';
    const full=part.startsWith('/')||part==='*'?part:(parent+'/'+part).replace(/\/$/,'')||'/';
    routes.push({path:full,index:attrs.some(a=>a.name?.getText(sf)==='index'),line:sf.getLineAndCharacterOfPosition(node.getStart(sf)).line+1,element:clean(attrs.find(a=>a.name?.getText(sf)==='element')?.initializer?.getText(sf)??''),status:'NOT TESTED'});return;
  }
  ts.forEachChild(node,child=>routeVisit(child,parent));
}
routeVisit(sf);
function closure(name,seen=new Set()){
  if(seen.has(name))return seen;seen.add(name);for(const other of imports[name]??[])closure(other,seen);return seen;
}
const pages=[...sources.keys()].filter(n=>n.includes('/pages/'));
const trace=pages.map(page=>{const reachable=closure(page);return {page,source_files:[...reachable].sort(),potential_requests:requests.filter(r=>reachable.has(r.file)).map(r=>({file:r.file,line:r.line,callee:r.callee,arguments:r.arguments})),status:'STATIC_REACHABILITY_ONLY',limitation:'Imports may be conditional or unused; actual handler execution must be separately verified. Ancestor Auth/GA providers can add requests.'};});
const result={scope:'CURRENT_WORKING_TREE_STATIC_SYNTAX; includes unfinished UI without modifying it',source_files:sources.size,route_definitions:routes,distinct_route_urls:[...new Set(routes.map(r=>r.path))],interactive_sites:features,http_callsites:requests,imports,page_traceability:trace};
const out=path.join(here,process.argv[2]??'frontend-static-inventory.json');fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:'STATIC_INVENTORY_CREATED',source_files:sources.size,route_definitions:routes.length,distinct_route_urls:result.distinct_route_urls.length,interactive_sites:features.length,http_callsites:requests.length,pages:pages.length}));
