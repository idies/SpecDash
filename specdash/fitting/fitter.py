from astropy.modeling import models, fitting
from specdash.models.base_model import Base
import numpy as np

class FittingModels(Base):
    GAUSSIAN_PLUS_LINEAR = "gaussian + linear"
    LORENTZIAN_PLUS_LINEAR = "lorentzian + linear"
    VOIGT_PLUS_LINEAR = "voigt + linear"
    GAUSSIAN = "gaussian"
    LORENTZIAN = "lorentzian"
    VOIGT = "voigt"
    CHEBYSHEV_1 = "chebyshev 1"
    CHEBYSHEV_2 = "chebyshev 2"
    CHEBYSHEV_3 = "chebyshev 3"
    POLYNOMIAL_1 = "polynomial 1"
    POLYNOMIAL_2 = "polynomial 2"
    POLYNOMIAL_3 = "polynomial 3"
    CUSTOM = "custom"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        methods = {func for func in dir(FittingModels) if callable(getattr(FittingModels, func))}
        return [v for k,v in FittingModels.__dict__.items() if k not in methods and not k.startswith('__')]

fitting_models_list = FittingModels.get_list()
default_fitting_models = [FittingModels.GAUSSIAN_PLUS_LINEAR, FittingModels.LORENTZIAN_PLUS_LINEAR,
                          FittingModels.VOIGT_PLUS_LINEAR,
                          FittingModels.GAUSSIAN, FittingModels.LORENTZIAN, FittingModels.VOIGT,
                          FittingModels.CHEBYSHEV_1,FittingModels.CHEBYSHEV_2,FittingModels.CHEBYSHEV_3,
                          FittingModels.POLYNOMIAL_1,FittingModels.POLYNOMIAL_2,FittingModels.POLYNOMIAL_3
                          ]


class ModelFitter(Base):

    def __init__(self, model=None, fitter=None, model_type=FittingModels.CUSTOM):
        """

        Parameters
        ----------
        model
        fitter
        model_type
        """
        self.model = model
        self.fitter = fitter
        self.model_type = model_type
        self.fitted_model = None

    def set_model_fitter(self, model, fitter, model_type=FittingModels.CUSTOM):
        self.model = model
        self.fitter = fitter
        self.model_type = model_type
        self.fitted_model = None

    @staticmethod
    def get_model_with_fitter(model_type, x, y):
        min_x, max_x = np.min(x), np.max(x)
        location_param = np.mean(x)
        amplitude_param = np.max(np.abs(y))
        spread_param = (max_x - min_x) / len(x)

        if model_type == FittingModels.GAUSSIAN_PLUS_LINEAR:
            model = models.Gaussian1D(amplitude=amplitude_param, mean=location_param,
                                      stddev=spread_param) + models.Polynomial1D(degree=1)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.LORENTZIAN_PLUS_LINEAR:
            model = models.Lorentz1D(amplitude=amplitude_param, x_0=location_param,
                                     fwhm=spread_param) + models.Polynomial1D(degree=1)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.VOIGT_PLUS_LINEAR:
            model = models.Voigt1D(x_0=location_param, amplitude_L=amplitude_param, fwhm_L=spread_param,
                                   fwhm_G=spread_param) + models.Polynomial1D(degree=1)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.GAUSSIAN:
            model = models.Gaussian1D(amplitude=amplitude_param, mean=location_param, stddev=spread_param)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.LORENTZIAN:
            model = models.Lorentz1D(amplitude=amplitude_param, x_0=location_param, fwhm=spread_param)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.VOIGT:
            model = models.Voigt1D(x_0=location_param, amplitude_L=amplitude_param, fwhm_L=spread_param, fwhm_G=spread_param)
            fitter = fitting.LevMarLSQFitter()

        elif model_type == FittingModels.CHEBYSHEV_1:
            model = models.Chebyshev1D(degree=1)
            fitter = fitting.LinearLSQFitter()

        elif model_type == FittingModels.CHEBYSHEV_2:
            model = models.Chebyshev1D(degree=2)
            fitter = fitting.LinearLSQFitter()

        elif model_type == FittingModels.CHEBYSHEV_3:
            model = models.Chebyshev1D(degree=3)
            fitter = fitting.LinearLSQFitter()

        elif model_type == FittingModels.POLYNOMIAL_1:
            model = models.Polynomial1D(degree=1)
            fitter = fitting.LinearLSQFitter()

        elif model_type == FittingModels.POLYNOMIAL_2:
            model = models.Polynomial1D(degree=2)
            fitter = fitting.LinearLSQFitter()

        elif model_type == FittingModels.POLYNOMIAL_3:
            model = models.Polynomial1D(degree=3)
            fitter = fitting.LinearLSQFitter()

        else:
            raise Exception("Model " + str(model_type) + " not in default models list.")

        return model,fitter



    def get_fit(self, x, y, weights=None):
        self.fitted_model = self.fitter(self.model, x, y, weights=weights)
        fitting_parameters = {x: y for (x, y) in zip(self.fitted_model.param_names, self.fitted_model.parameters)}
        parameter_errors = np.sqrt(np.diag(self.fitter.fit_info['param_cov'])) if self.fitter.fit_info['param_cov'] is not None else None
        return {'fitted_parameters':fitting_parameters,'parameter_errors':parameter_errors}

    def get_fitted_model(self):
        return self.fitted_model
