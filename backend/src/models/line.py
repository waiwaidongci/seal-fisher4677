from sqlalchemy import Column,Integer,String,JSON
from src.config.database import Base
class SealLine(Base):
    __tablename__='lines'
    id=Column(Integer,primary_key=True)
    name=Column(String(120),unique=True,nullable=False)
    status=Column(String(20),nullable=False,default='registering')  # registering/dispatching/completed
    version=Column(Integer,nullable=False,default=1)  # 名单与排法按同一版锁定
    arrangement=Column(JSON,nullable=False)  # 整线排法，仅服务端持有，完工前不随接口暴露未派工艺
    created_by=Column(String(120),nullable=False)
    created_at=Column(String(40),nullable=False)
Line=SealLine
