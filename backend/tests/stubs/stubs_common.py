class Field:
    def __init__(self,name): self.name=name
    def __eq__(self,other): return lambda obj: getattr(obj,self.name)==other
    def desc(self): return ('desc',self)
