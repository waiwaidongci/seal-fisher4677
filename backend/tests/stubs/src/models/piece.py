from stubs_common import Field
class Piece:
    id=Field('id'); line_id=Field('line_id'); seq=Field('seq'); version=Field('version')
    shift=Field('shift'); roll=Field('roll'); process=Field('process'); status=Field('status')
    station=Field('station'); operator=Field('operator'); claimed_at=Field('claimed_at')
    judgment=Field('judgment'); judged_at=Field('judged_at')
    def __init__(self,**kw):
        for k in ('id','line_id','seq','version','shift','roll','process','status','station','operator','claimed_at','judgment','judged_at'): setattr(self,k,kw.get(k))
