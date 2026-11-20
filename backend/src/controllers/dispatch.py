from src.services import dispatch
# Controllers keep endpoint contracts separate from persistence and calculation.
def list_lines(db): return dispatch.list_lines(db)
def create_line(db,data,user): return dispatch.create_line(db,data,user)
def get_line(db,id): return dispatch.get_line(db,id)
def correct_roster(db,id,data,user): return dispatch.correct_roster(db,id,data,user)
def claim(db,id,data,user): return dispatch.claim(db,id,data,user)
def judge(db,id,data,user): return dispatch.judge(db,id,data,user)
