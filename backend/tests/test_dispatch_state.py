"""dispatch 服务状态机测试：python3 tests/test_dispatch_state.py（仅标准库）。

用桩替代 sqlalchemy/fastapi/模型，内存版 FakeDB 模拟串行事务与唯一约束，
直接运行真实的 src/services/dispatch.py 业务逻辑；行锁并发语义由 MySQL
InnoDB 的 SELECT ... FOR UPDATE 保证，不在本测试范围内。
"""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))      # 真实的 src.services.lineup / dispatch
sys.path.insert(0,str(HERE/'stubs'))     # 桩优先（namespace 包合并）
from src.models.line import Line
from src.models.piece import Piece
from src.services import dispatch
from fastapi import HTTPException

def is_valid(roster,assign):
    for dim in (0,1):
        count={}
        for piece,c in zip(roster,assign):
            a,b=count.get(piece[dim],(0,0))
            count[piece[dim]]=(a+(c=='A'),b+(c=='B'))
        if any(a!=b for a,b in count.values()): return False
    return not any(assign[i]==assign[i+1]==assign[i+2] for i in range(len(assign)-2))

class Scalars:
    def __init__(self,rows): self.rows=rows
    def first(self): return self.rows[0] if self.rows else None
    def __iter__(self): return iter(self.rows)

class FakeDB:
    def __init__(self): self.store={Line:[],Piece:[]}; self.audit=[]; self.seq={Line:0,Piece:0}
    def scalars(self,q):
        rows=[r for r in self.store[q.model] if all(c(r) for c in q.conds)]
        for k in reversed(q.keys):
            if isinstance(k,tuple): rows.sort(key=lambda r:getattr(r,k[1].name),reverse=True)
            else: rows.sort(key=lambda r:getattr(r,k.name))
        return Scalars(rows)
    def scalar(self,q): return self.scalars(q).first()
    def get(self,model,id): return next((r for r in self.store[model] if r.id==id),None)
    def add(self,obj):
        if obj.id is None:
            self.seq[type(obj)]+=1; obj.id=self.seq[type(obj)]
        self.store[type(obj)].append(obj)
    def delete(self,obj): self.store[type(obj)].remove(obj)
    def flush(self):
        names=[l.name for l in self.store[Line]]
        assert len(names)==len(set(names)),'派工批名称唯一约束被违反'
        keys=[(p.line_id,p.seq) for p in self.store[Piece]]
        assert len(keys)==len(set(keys)),'试件(line_id,seq)唯一约束被违反'
    def commit(self): self.flush()

class U: email='analyst@demo.local'
class D:
    def __init__(self,**kw): self.__dict__.update(kw)

def expect(code,fn,*args):
    try: fn(*args)
    except HTTPException as e:
        assert e.status_code==code,(code,e.status_code,e.detail); return e.detail
    raise AssertionError(f'应当返回{code}')

ROSTER=[('早班','卷-01'),('早班','卷-02'),('中班','卷-01'),('中班','卷-02'),('早班','卷-03'),('早班','卷-04'),('中班','卷-03'),('中班','卷-04')]
def mkpieces(roster): return [D(shift=s,roll=r) for s,r in roster]

def main():
    db=FakeDB()
    d=expect(422,dispatch.create_line,db,D(name='坏批',pieces=mkpieces([('早','卷1'),('早','卷1'),('晚','卷2')])),U())
    assert '班次' in d and '奇数' in d; print('ok 奇数班次拒绝：',d)
    line=dispatch.create_line(db,D(name='一批',pieces=mkpieces(ROSTER)),U())
    assert line['status']=='registering' and line['version']==1 and line['piece_count']==8
    assert all(p['process'] is None for p in line['pieces']); print('ok 登记新批：8件，未派工艺保密')
    d=expect(409,dispatch.correct_roster,db,1,D(version=9,pieces=mkpieces(ROSTER)),U())
    print('ok 版本不符拒绝：',d)
    line2=dispatch.correct_roster(db,1,D(version=1,pieces=mkpieces(ROSTER[:4])),U())
    assert line2['version']==2 and line2['piece_count']==4
    assert len(db.get(Line,1).arrangement)==4; print('ok 整批更正到第2版，名单与排法同版更换')
    c1=dispatch.claim(db,1,D(station='1号工位'),U())
    assert c1['seq']==1 and c1['process'] in ('A','B') and not c1['reused']; print('ok 工位1领到第1件 工艺',c1['process'])
    d=expect(409,dispatch.claim,db,1,D(station='2号工位'),U())
    assert '1号工位' in d; print('ok 并发领取只派一方：',d)
    c2=dispatch.claim(db,1,D(station='1号工位'),U())
    assert c2['reused'] and c2['seq']==1 and c2['process']==c1['process']; print('ok 断线重试返回原领取结果')
    d=expect(409,dispatch.correct_roster,db,1,D(version=2,pieces=mkpieces(ROSTER)),U())
    print('ok 首件发出后锁定：',d)
    d=expect(409,dispatch.judge,db,1,D(station='2号工位',seq=1,judgment='合格'),U())
    print('ok 非领取工位不能交判定：',d)
    v=dispatch.judge(db,1,D(station='1号工位',seq=1,judgment='合格'),U())
    assert v['pieces'][0]['judgment']=='合格' and v['judged_count']==1
    c3=dispatch.claim(db,1,D(station='2号工位'),U())
    assert c3['seq']==2; print('ok 交回判定后揭下一件（工位2领到第2件）')
    v2=dispatch.judge(db,1,D(station='1号工位',seq=1,judgment='合格'),U())
    assert v2['pieces'][0]['judgment']=='合格'
    d=expect(409,dispatch.judge,db,1,D(station='1号工位',seq=1,judgment='不合格'),U())
    print('ok 判定幂等且不可覆盖：',d)
    d=expect(409,dispatch.judge,db,1,D(station='2号工位',seq=3,judgment='合格'),U())
    print('ok 未派件不能交判定：',d)
    dispatch.judge(db,1,D(station='2号工位',seq=2,judgment='不合格'),U())
    dispatch.claim(db,1,D(station='1号工位'),U()); dispatch.judge(db,1,D(station='1号工位',seq=3,judgment='合格'),U())
    dispatch.claim(db,1,D(station='1号工位'),U()); fin=dispatch.judge(db,1,D(station='1号工位',seq=4,judgment='合格'),U())
    assert fin['status']=='completed' and fin['judged_count']==4
    assert all(p['process'] for p in fin['pieces']); print('ok 完工后全部工艺公开：',[p['process'] for p in fin['pieces']])
    d=expect(409,dispatch.claim,db,1,D(station='1号工位'),U())
    print('ok 完工后无件可派：',d)
    assert is_valid(ROSTER[:4],db.get(Line,1).arrangement); print('ok 库存排法合规')
    acts=[a for _,a,_ in db.audit]
    assert acts==['line.create','line.correct']+['line.claim','line.judge']*4,acts
    print('ok 审计动作链完整：',acts)
    print('全部通过')

if __name__=='__main__': main()
