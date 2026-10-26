"""Validate real YAML shell heredocs as Python before any remote execution."""
from __future__ import annotations
import argparse,ast,json,re
from pathlib import Path
import yaml

HEREDOC=re.compile(r"<<(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))")
PYTHON=re.compile(r"(?:^|[;\s])(?:[^;\s]*/)?python(?:3(?:\.[0-9]+)?)?\b")

def inspect(path):
 w=yaml.safe_load(Path(path).read_text());records=[];errors=[]
 for job_name,job in w['jobs'].items():
  for step in job['steps']:
   if 'run' not in step:continue
   lines=step['run'].splitlines();i=0
   while i<len(lines):
    line=lines[i];match=HEREDOC.search(line)
    if not match:i+=1;continue
    marker=next(x for x in match.groups()[1:] if x is not None);strip_tabs=bool(match.group(1));start=i+1;end=start
    while end<len(lines) and (lines[end].lstrip('\t') if strip_tabs else lines[end])!=marker:end+=1
    if end==len(lines):raise ValueError('missing heredoc terminator '+marker)
    executable=bool(PYTHON.search(line[:match.start()]));python_source_file=bool(re.search(r'\.py[\"\']?\s*$',line[:match.start()]))
    if executable or python_source_file:
     source='\n'.join(lines[start:end])+'\n';record={'job':job_name,'step':step['name'],'marker':marker,'executable_inline_Python':executable,'generated_Python_file':python_source_file,'body_lines':end-start}
     try:ast.parse(source,filename=marker);record['AST_passed']=True
     except SyntaxError as exc:
      record.update(AST_passed=False,error_type='SyntaxError',line=exc.lineno,message=exc.msg);errors.append(dict(record))
     records.append(record)
    i=end+1
 return {'source_workflow':Path(path).name,'Python_heredoc_count':len(records),'executable_inline_Python_count':sum(x['executable_inline_Python'] for x in records),
  'all_embedded_and_generated_Python_AST_passed':not errors,'records':records,'failures':errors,'native_CAD_executed':False}

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('workflow',type=Path);a=ap.parse_args();r=inspect(a.workflow);print(json.dumps(r,indent=2));raise SystemExit(0 if r['all_embedded_and_generated_Python_AST_passed'] else 2)
