class Query:
    def __init__(self,model): self.model=model; self.conds=[]; self.keys=[]
    def where(self,*c): self.conds+=c; return self
    def with_for_update(self): return self
    def order_by(self,*k): self.keys+=k; return self
def select(model): return Query(model)
