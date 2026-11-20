from fastapi import APIRouter,Depends
from src.config.database import get_db
from src.middlewares.auth import current_user,writer
from src.schemas.line import LineInput,RosterInput,ClaimInput,JudgeInput
from src.controllers import dispatch
router=APIRouter()
@router.get('/lines')
def list_lines(db=Depends(get_db),user=Depends(current_user)): return dispatch.list_lines(db)
@router.post('/lines')
def create_line(data:LineInput,db=Depends(get_db),user=Depends(writer)): return dispatch.create_line(db,data,user)
@router.get('/lines/{id}')
def get_line(id:int,db=Depends(get_db),user=Depends(current_user)): return dispatch.get_line(db,id)
@router.put('/lines/{id}/roster')
def correct_roster(id:int,data:RosterInput,db=Depends(get_db),user=Depends(writer)): return dispatch.correct_roster(db,id,data,user)
@router.post('/lines/{id}/claim')
def claim(id:int,data:ClaimInput,db=Depends(get_db),user=Depends(writer)): return dispatch.claim(db,id,data,user)
@router.post('/lines/{id}/judge')
def judge(id:int,data:JudgeInput,db=Depends(get_db),user=Depends(writer)): return dispatch.judge(db,id,data,user)
