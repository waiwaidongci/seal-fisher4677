from stubs_common import Field
class Line:
    id=Field('id'); name=Field('name'); status=Field('status'); version=Field('version')
    arrangement=Field('arrangement'); created_by=Field('created_by'); created_at=Field('created_at')
    def __init__(self,**kw):
        for k in ('id','name','status','version','arrangement','created_by','created_at'): setattr(self,k,kw.get(k))
