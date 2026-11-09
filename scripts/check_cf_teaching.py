"""Exhaustive small-domain checks for cf_div2_teaching.md (standard library only)."""

from itertools import product, combinations
from functools import lru_cache

# Compare the exchange formula with every positive composition.
bank=0
for n in range(1,13):
    for k in range(1,n+1):
        best=max(sum(2**(v-u) for u,v in zip((0,)+cuts,cuts+(n,))) for cuts in combinations(range(1,n),k-1))
        assert best==2**(n-k+1)+2*(k-1)
        bank+=1

# Enumerate every operation choice, retaining all reachable sums and maxima.
prefix=0
for n in range(2,7):
    for a in product(range(-2,3),repeat=n):
        states = {(a[0], a[0])}
        lo = hi = ans = a[0]
        for x in a[1:]:
            states={(s+x+t*s,max(v,x+t*s)) for s,v in states for t in (-1,0,1)}
            ans=max(ans,x+max(abs(lo),abs(hi)))
            lo,hi=x+min(0,2*lo),x+max(0,2*hi)
        assert ans==max(v for s,v in states),a
        prefix+=1

# Compare four generated patterns with every completion of every ternary string.
domino=0
for n in range(2,9):
    for s in product('01?',repeat=n):
        brute=0
        for bits in product((0,1),repeat=s.count('?')):
            it = iter(bits)
            a = [next(it) if c == '?' else int(c) for c in s]
            brute+=all(a[i]+a[i+1]!=a[i+1]+a[i+2] for i in range(n-2))
        count=0
        for p,q in product((0,1),repeat=2):
            a=[p,q]
            for i in range(2, n):
                a.append(1 - a[i-2])
            count+=all(c=='?' or int(c)==x for c,x in zip(s,a))
        assert count==brute,s
        domino+=1

# Independent search over groups of original leaves, not the proposed sorted pairs.
merge=0
universe=range(1,10)
for n in range(1,8):
    for a in combinations(universe,n):
        rest=[x for x in universe if x not in a]
        for m in range(1,min(3,len(rest))+1):
            for b in combinations(rest,m):
                @lru_cache(None)
                def assign(i,mask):
                    if i == m:
                        # Absorb unused leaves without changing a target.
                        return True
                    sub=mask
                    while sub:
                        vals=[a[j] for j in range(n) if sub>>j&1]
                        if min(vals) < b[i] < max(vals) and assign(i+1, mask^sub):
                            return True
                        sub=(sub-1)&mask
                    return False
                brute=assign(0,(1<<n)-1)
                predicted=n>=2*m and all(a[i]<b[i]<a[n-m+i] for i in range(m))
                assert predicted==brute,(a,b)
                merge+=1
print(dict(bank=bank,prefix=prefix,domino=domino,merge=merge))
