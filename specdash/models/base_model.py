

class Base():
    def __init__(self):
        pass

    def from_dict(self, dict):
        for attr in self.__dict__:
            self.__dict__[attr] = dict[attr]

    def return_class(self):
        return self

    def to_dict(self):
        d = self.__dict__
        for key in d:
            if hasattr(d[key],"__class__") and hasattr(d[key],"__dict__") and callable(getattr(d[key],"to_dict")):
                d[key] = d[key].to_dict()
        return d

    def to_dict2(self, classkey=None):
        if isinstance(self, dict):
            data = {}
            for (k, v) in self.items():
                data[k] = self.to_dict(v, classkey)
            return data
        elif hasattr(self, "_ast"):
            return self.to_dict(self._ast())
        elif hasattr(self, "__iter__") and not isinstance(self, str):
            return [self.to_dict(v, classkey) for v in self]
        elif hasattr(self, "__dict__"):
            data = dict([(key, self.to_dict(value, classkey))
                         for key, value in self.__dict__.items()
                         if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(self, "__class__"):
                data[classkey] = self.__class__.__name__
            return data
        else:
            return self



    @classmethod
    def to_string(self):
        return str(self.to_dict())

    def get_attributes(self):
        return [t for t in self.__dict__]
