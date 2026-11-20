"""连续试封整线排法：搜索、精确计数与等概率抽样。

业务约束：名单按加工顺序固定，逐件指派工艺 A/B；
每个班次内 A/B 件数相等，每个卷号内 A/B 件数相等；
同一工艺连续出现至多两件；整线最多 32 件。

方法：带备忘录的深搜对合规排法精确计数，再按各分支计数比例
逐位随机走取，保证每套合规排法被抽中的概率严格相等。
无解抛 Infeasible（携带可展示原因），超过5秒抛 SearchTimeout；
两者都由上层转为拒绝派工。
"""
import random,time
from collections import Counter

MAX_PIECES=32
SEARCH_TIMEOUT=5.0  # 秒；超时与无解一样拒绝派工

class Infeasible(ValueError): pass
class SearchTimeout(TimeoutError): pass

def _pair(x):
    if isinstance(x,dict): return x.get('shift'),x.get('roll')
    if isinstance(x,(tuple,list)) and len(x)==2: return x[0],x[1]
    return getattr(x,'shift',None),getattr(x,'roll',None)

def normalize_roster(pieces):
    """把输入整理成 [(班次, 卷号), ...]；不合法时抛 Infeasible 并说明原因。"""
    roster=[]
    for i,raw in enumerate(list(pieces or []),1):
        shift,roll=_pair(raw)
        shift=str(shift or '').strip()
        roll=str(roll or '').strip()
        if not shift: raise Infeasible(f'第{i}件未登记班次')
        if not roll: raise Infeasible(f'第{i}件未登记卷号')
        if len(shift)>40 or len(roll)>40: raise Infeasible(f'第{i}件的班次/卷号各限40字')
        roster.append((shift,roll))
    if not roster: raise Infeasible('名单为空，无法派工')
    if len(roster)>MAX_PIECES: raise Infeasible(f'整线最多{MAX_PIECES}件，当前登记{len(roster)}件')
    return roster

def _prepare(roster):
    """把班次/卷号映射为下标，预计算各组A件配额与后缀剩余件数；奇数组直接判无解。"""
    shifts=sorted({s for s,_ in roster})
    rolls=sorted({r for _,r in roster})
    si={s:i for i,s in enumerate(shifts)}
    ri={r:i for i,r in enumerate(rolls)}
    seq=[(si[s],ri[r]) for s,r in roster]
    sc=Counter(s for s,_ in seq)
    rc=Counter(r for _,r in seq)
    for s in sorted(sc):
        if sc[s]%2: raise Infeasible(f'班次「{shifts[s]}」共{sc[s]}件为奇数，班内A/B无法相等')
    for r in sorted(rc):
        if rc[r]%2: raise Infeasible(f'卷号「{rolls[r]}」共{rc[r]}件为奇数，卷内A/B无法相等')
    sb0=tuple(sc[s]//2 for s in range(len(shifts)))  # 每班剩余可派A件数
    rb0=tuple(rc[r]//2 for r in range(len(rolls)))   # 每卷剩余可派A件数
    n=len(seq)
    sleft=[0]*n; rleft=[0]*n
    seen=Counter()
    for i in range(n-1,-1,-1):
        seen[seq[i][0]]+=1; sleft[i]=seen[seq[i][0]]  # 自第i件起同班剩余件数
    seen=Counter()
    for i in range(n-1,-1,-1):
        seen[seq[i][1]]+=1; rleft[i]=seen[seq[i][1]]  # 自第i件起同卷剩余件数
    return seq,sb0,rb0,sleft,rleft

def _make_dfs(seq,sleft,rleft,deadline):
    n=len(seq); memo={}; visits=0
    def dfs(i,last,run,sb,rb):
        """从第i件起、上一工艺为last且已连续run件的合规续排总数。"""
        nonlocal visits
        if i==n: return 1
        key=(i,last,run,sb,rb)
        hit=memo.get(key)
        if hit is not None: return hit
        visits+=1
        if not visits&511 and time.monotonic()>deadline:
            raise SearchTimeout('合规排法搜索超过5秒')
        s,r=seq[i]; total=0
        for choice in (0,1):  # 0=A 1=B
            if choice==last and run==2: continue  # 同工艺至多连续两件
            if choice==0:
                if not sb[s] or not rb[r]: continue  # 该班/卷的A件配额已用完
                nsb=sb[:s]+(sb[s]-1,)+sb[s+1:]
                nrb=rb[:r]+(rb[r]-1,)+rb[r+1:]
            else:
                if sleft[i]-sb[s]<=0 or rleft[i]-rb[r]<=0: continue  # 该班/卷剩余件必须全排B才够
                nsb=sb; nrb=rb
            total+=dfs(i+1,choice,run+1 if choice==last else 1,nsb,nrb)
        memo[key]=total
        return total
    return dfs

def count_lineups(roster,timeout=SEARCH_TIMEOUT):
    """合规整线排法总数；0 表示无解。供校验与测试使用。"""
    seq,sb0,rb0,sleft,rleft=_prepare(roster)
    dfs=_make_dfs(seq,sleft,rleft,time.monotonic()+timeout)
    return dfs(0,-1,0,sb0,rb0)

def sample_lineup(roster,timeout=SEARCH_TIMEOUT,rng=None):
    """从全部合规整线排法中等概率抽取一套，返回 ['A','B',...]。"""
    seq,sb0,rb0,sleft,rleft=_prepare(roster)
    n=len(seq)
    dfs=_make_dfs(seq,sleft,rleft,time.monotonic()+timeout)
    total=dfs(0,-1,0,sb0,rb0)
    if not total:
        raise Infeasible('该名单在「每班/每卷A/B相等、同工艺连续至多两件」下无合规排法')
    rng=rng or random.SystemRandom()
    out=[]; last=-1; run=0; sb=sb0; rb=rb0
    for i in range(n):
        s,r=seq[i]; ways=[0,0]
        for choice in (0,1):
            if choice==last and run==2: continue
            if choice==0:
                if not sb[s] or not rb[r]: continue
                nsb=sb[:s]+(sb[s]-1,)+sb[s+1:]
                nrb=rb[:r]+(rb[r]-1,)+rb[r+1:]
            else:
                if sleft[i]-sb[s]<=0 or rleft[i]-rb[r]<=0: continue
                nsb=sb; nrb=rb
            ways[choice]=dfs(i+1,choice,run+1 if choice==last else 1,nsb,nrb)
        pick=rng.randrange(ways[0]+ways[1])  # 整数按比例抽，严格等概率
        choice=0 if pick<ways[0] else 1
        out.append('AB'[choice])
        if choice==0:
            sb=sb[:s]+(sb[s]-1,)+sb[s+1:]
            rb=rb[:r]+(rb[r]-1,)+rb[r+1:]
        run=run+1 if choice==last else 1
        last=choice
    return out
