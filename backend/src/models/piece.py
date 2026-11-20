from sqlalchemy import Column,Integer,String,ForeignKey,UniqueConstraint
from src.config.database import Base
class SealPiece(Base):
    __tablename__='line_pieces'
    __table_args__=(UniqueConstraint('line_id','seq'),)
    id=Column(Integer,primary_key=True)
    line_id=Column(Integer,ForeignKey('lines.id'),nullable=False)
    seq=Column(Integer,nullable=False)  # 加工顺序，从1开始
    version=Column(Integer,nullable=False)  # 所属名单版本
    shift=Column(String(40),nullable=False)  # 班次
    roll=Column(String(40),nullable=False)  # 卷号
    process=Column(String(1),nullable=False)  # 已抽排工艺 A/B
    status=Column(String(20),nullable=False,default='pending')  # pending/claimed/judged
    station=Column(String(40),nullable=True)  # 领取工位
    operator=Column(String(120),nullable=True)  # 领取账号
    claimed_at=Column(String(40),nullable=True)
    judgment=Column(String(10),nullable=True)  # 合格/不合格
    judged_at=Column(String(40),nullable=True)
Piece=SealPiece
