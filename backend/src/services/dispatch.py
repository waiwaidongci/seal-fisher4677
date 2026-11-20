from sqlalchemy import select
from fastapi import HTTPException
from src.models.line import Line
from src.models.piece import Piece
from src.services import lineup
from src.services.audits import log
from src.utils.serializers import now

JUDGMENTS=('合格','不合格')

def _lock(db,id):
    """以行锁读取派工批；领取、判定、整批更正都在同一把锁内串行。"""
    line=db.scalars(select(Line).where(Line.id==id).with_for_update()).first()
    if not line: raise HTTPException(404,'派工批不存在')
    return line

def _pieces(db,id):
    return list(db.scalars(select(Piece).where(Piece.line_id==id).order_by(Piece.seq)))

def _public(line,pieces):
    """对外视图：完工前不暴露未派工艺。"""
    done=line.status=='completed'
    out=[]
    for p in pieces:
        x={'seq':p.seq,'shift':p.shift,'roll':p.roll,'status':p.status,'version':p.version,
           'station':p.station if p.status!='pending' else None,
           'judgment':p.judgment if p.status=='judged' else None,
           'process':p.process if (p.status!='pending' or done) else None}
        out.append(x)
    return {'id':line.id,'name':line.name,'status':line.status,'version':line.version,
            'created_by':line.created_by,'created_at':line.created_at,
            'piece_count':len(pieces),'judged_count':sum(1 for p in pieces if p.status=='judged'),
            'pieces':out}

def _sample_or_refuse(roster):
    try: return lineup.sample_lineup(roster)
    except lineup.Infeasible as e: raise HTTPException(422,f'无法派工：{e}')
    except lineup.SearchTimeout: raise HTTPException(422,'无法派工：合规排法搜索超过5秒，请调整班次/卷号结构后重试')

def _roster_or_refuse(pieces):
    try: return lineup.normalize_roster(pieces)
    except lineup.Infeasible as e: raise HTTPException(422,f'无法派工：{e}')

def list_lines(db):
    out=[]
    for line in db.scalars(select(Line).order_by(Line.id.desc())):
        view=_public(line,_pieces(db,line.id));view.pop('pieces');out.append(view)
    return out

def get_line(db,id):
    line=db.get(Line,id)
    if not line: raise HTTPException(404,'派工批不存在')
    return _public(line,_pieces(db,id))

def create_line(db,data,user):
    if db.scalar(select(Line).where(Line.name==data.name)): raise HTTPException(409,'派工批名称已存在')
    roster=_roster_or_refuse(data.pieces)
    arrangement=_sample_or_refuse(roster)
    line=Line(name=data.name,status='registering',version=1,arrangement=arrangement,created_by=user.email,created_at=now())
    db.add(line);db.flush()
    for i,((shift,roll),proc) in enumerate(zip(roster,arrangement),1):
        db.add(Piece(line_id=line.id,seq=i,version=1,shift=shift,roll=roll,process=proc,status='pending'))
    log(db,user,'line.create',f'{line.id} {data.name} {len(roster)}件 第1版')
    db.commit()
    return get_line(db,line.id)

def correct_roster(db,id,data,user):
    """首件发出前整批更正：名单与排法在同一事务内换成新版本。"""
    line=_lock(db,id)
    pieces=_pieces(db,id)
    if any(p.status!='pending' for p in pieces): raise HTTPException(409,'首件已发出，名单与排法已锁定，不可整批更正')
    if data.version!=line.version: raise HTTPException(409,f'名单已更正为第{line.version}版，请刷新后基于最新版本再改')
    roster=_roster_or_refuse(data.pieces)
    arrangement=_sample_or_refuse(roster)
    line.version+=1
    line.arrangement=arrangement
    for p in pieces: db.delete(p)
    db.flush()
    for i,((shift,roll),proc) in enumerate(zip(roster,arrangement),1):
        db.add(Piece(line_id=line.id,seq=i,version=line.version,shift=shift,roll=roll,process=proc,status='pending'))
    log(db,user,'line.correct',f'{id} 更正为第{line.version}版 {len(roster)}件')
    db.commit()
    return get_line(db,id)

def _claim_view(line,p,reused):
    return {'line_id':line.id,'version':line.version,'seq':p.seq,'shift':p.shift,'roll':p.roll,
            'process':p.process,'station':p.station,'status':p.status,'reused':reused}

def claim(db,id,data,user):
    """领取下一件：并发只派一方；同工位断线重试返回原领取结果。"""
    station=data.station.strip()
    if not station: raise HTTPException(422,'请填写工位')
    line=_lock(db,id)
    if line.status=='completed': raise HTTPException(409,'本批已完工，无件可派')
    current=next((p for p in _pieces(db,id) if p.status!='judged'),None)
    if current is None:
        line.status='completed';log(db,user,'line.complete',id);db.commit()
        raise HTTPException(409,'本批已完工，无件可派')
    if current.status=='claimed':
        if current.station==station: return _claim_view(line,current,True)  # 断线重试：不重复派工
        raise HTTPException(409,f'第{current.seq}件已由工位「{current.station}」领取，待其交回判定后才揭下一件')
    current.status='claimed';current.station=station;current.operator=user.email;current.claimed_at=now()
    if line.status=='registering': line.status='dispatching'
    log(db,user,'line.claim',f'{id} 第{current.seq}件 派给工位「{station}」 工艺{current.process}')
    db.commit()
    return _claim_view(line,current,False)

def judge(db,id,data,user):
    """交回判定：只有领取工位能交；同判定重试返回原结果，不同判定拒绝覆盖。"""
    if data.judgment not in JUDGMENTS: raise HTTPException(422,'判定只能为 合格/不合格')
    station=data.station.strip()
    line=_lock(db,id)
    pieces=_pieces(db,id)
    p=next((x for x in pieces if x.seq==data.seq),None)
    if not p: raise HTTPException(404,'试件不存在')
    if p.status=='pending': raise HTTPException(409,f'第{p.seq}件尚未派发，不能交回判定')
    if p.station!=station: raise HTTPException(409,f'第{p.seq}件由工位「{p.station}」领取，只能由该工位交回判定')
    if p.status=='judged':
        if p.judgment==data.judgment: return _public(line,pieces)  # 断线重试：返回原判定结果
        raise HTTPException(409,f'第{p.seq}件已判定为「{p.judgment}」，判定不可覆盖')
    p.judgment=data.judgment;p.status='judged';p.judged_at=now()
    if all(x.status=='judged' for x in pieces): line.status='completed'
    log(db,user,'line.judge',f'{id} 第{p.seq}件 工位「{station}」 判定{p.judgment}')
    db.commit()
    return get_line(db,id)
