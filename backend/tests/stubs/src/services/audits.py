def log(db,user,action,detail): db.audit.append((user,action,str(detail)))
