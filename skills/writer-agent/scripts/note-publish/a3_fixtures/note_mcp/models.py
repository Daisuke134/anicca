class Session:
    def __init__(self, **kw): self.__dict__.update(kw)
class ArticleInput:
    def __init__(self, title=None, body=None, tags=None):
        self.title=title; self.body=body; self.tags=tags
