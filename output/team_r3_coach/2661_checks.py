import subprocess,tempfile,json,itertools,pathlib
out={}
with tempfile.TemporaryDirectory() as td:
 def run(s,inp):
  exe=pathlib.Path(td)/str(s)
  if not exe.exists(): subprocess.run(['g++','-std=c++20','-O2','-x','c++',f'data/team_r3/code/{s}.txt','-o',str(exe)],check=True)
  return subprocess.run([str(exe)],input=inp,text=True,capture_output=True,timeout=15).stdout.strip()
 cases={'B_marginals':('4 4 1\n1 1 0\n4\n1 1 1\n2 2 1\n3 3 1\n4 4 1\n','0',[3191526,3191627,3192234,3192623,3192772,3192807]),'B_zero_y':('4 1 4\n1 0 1\n4\n1 1 1\n2 1 4\n3 1 2\n4 1 3\n','1',[3192234,3192623,3192772,3192807]),'J_high_carry':('1\n2 2\n14 16\n0 1\n','1',[3192569,3192839,3196588]),'J_high_bits':('1\n2 2\n0 6\n0 1\n','0',[3192569,3192839,3196588]),'G_decrease':('1\n7 3 4\n','YES',[3191584,3191724,3191747,3191789,3191819,3191865])}
 for name,(inp,expect,ids) in cases.items():
  out[name]={'input':inp,'expected':expect,'outputs':{str(s):run(s,inp) for s in ids}}
 ss=[''.join(x) for n in range(3,10) for x in itertools.product('01',repeat=n)]
 expected=[format(max(int(s[:i],2)^int(s[i+1:],2) for i in range(1,len(s)-1)),'b') for s in ss]
 inp=str(len(ss))+'\n'+'\n'.join(ss)+'\n'
 for sid in [3191371,3191395,3191415]:
  vals=run(sid,inp).splitlines(); bad=[{'input':s,'expected':e,'actual':v} for s,e,v in zip(ss,expected,vals) if e!=v]
  out[str(sid)]={'exhaustive_binary_lengths':[3,9],'cases':len(ss),'failures':len(bad),'first_examples':bad[:5]}
pathlib.Path('output/team_r3_coach/2661_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
