import subprocess,tempfile,itertools,json,pathlib
out={}
with tempfile.TemporaryDirectory() as td:
 def exe(s,ubsan=False):
  p=pathlib.Path(td)/str(s)
  subprocess.run(['g++','-std=c++20','-O1','-x','c++',f'data/team_r3/code/{s}.txt','-o',str(p)]+(['-fsanitize=undefined','-fno-sanitize-recover=all'] if ubsan else []),check=True)
  return p
 cases=[(n,m,a) for n in [2,3] for m in range(n) for a in itertools.combinations_with_replacement(range(1,13),n)]
 def f(x,y):
  best=abs(x-y);k=0
  while x>1:
   x//=2;k+=1;best=min(best,k+abs(x-y))
  return best
 expected=[min(sum(sorted(f(x,y) for x in a)[:n-m]) for y in range(1,max(a)+1)) for n,m,a in cases]
 inp=str(len(cases))+'\n'+''.join(f'{n} {m}\n'+ ' '.join(map(str,a))+'\n' for n,m,a in cases)
 for s in [3130459,3130682,3131303]:
  program=exe(s)
  vs=[]
  for begin in range(0,len(cases),10):
   batch=cases[begin:begin+10]
   text=str(len(batch))+'\n'+''.join(f'{n} {m}\n'+' '.join(map(str,a))+'\n' for n,m,a in batch)
   r=subprocess.run([str(program)],input=text,text=True,capture_output=True,timeout=30)
   vs.extend(map(int,r.stdout.split()))
  bad=[{'n':n,'m':m,'a':a,'expected':e,'actual':v} for (n,m,a),e,v in zip(cases,expected,vs) if e!=v]
  out[str(s)]={'cases':len(cases),'failures':len(bad),'examples':bad[:4]}
 for s in [3129901,3129936]:
  r=subprocess.run([str(exe(s,True))],input='1\n1 1\n',text=True,capture_output=True)
  out[str(s)]={'input':'1\n1 1\n','returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 edges=[(1,i) for i in range(2,9)]+[(i,9+(i-2)*12+j) for i in range(2,9) for j in range(12)]
 inp='92\n'+''.join(f'{u} {v}\n' for u,v in edges)
 for s in [3131165,3131402]:
  r=subprocess.run([str(exe(s,True))],input=inp,text=True,capture_output=True)
  out[str(s)]={'input':inp,'returncode':r.returncode,'stderr':r.stderr}
pathlib.Path('output/team_r3_coach/1053_checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
