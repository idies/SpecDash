from specdash.models.base_model import Base

class FittingModels(Base):
    GAUSSIAN_PLUS_LINEAR = "gaussian + linear"
    LORENTZIAN_PLUS_LINEAR = "lorentzian + linear"
    VOIGT_PLUS_LINEAR = "voigt + linear"
    USER_DEFINED = "user-defined"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        methods = {func for func in dir(FittingModels) if callable(getattr(FittingModels, func))}
        return [v for k,v in FittingModels.__dict__.items() if k not in methods and not k.startswith('__')]

fitting_models_list = FittingModels.get_list()
