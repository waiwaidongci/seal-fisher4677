from pydantic import BaseModel,Field
class SealPieceInput(BaseModel):
    shift:str=Field(min_length=1,max_length=40)
    roll:str=Field(min_length=1,max_length=40)
class SealLineInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    pieces:list[SealPieceInput]=Field(min_length=1,max_length=32)
class RosterInput(BaseModel):
    version:int=Field(ge=1)
    pieces:list[SealPieceInput]=Field(min_length=1,max_length=32)
class ClaimInput(BaseModel):
    station:str=Field(min_length=1,max_length=40)
class JudgeInput(BaseModel):
    station:str=Field(min_length=1,max_length=40)
    seq:int=Field(ge=1,le=32)
    judgment:str=Field(min_length=1,max_length=10)
PieceInput=SealPieceInput
LineInput=SealLineInput
