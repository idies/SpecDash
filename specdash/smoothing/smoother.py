from specdash.models.base_model import Base
from astropy.convolution import convolve, Gaussian1DKernel, Box1DKernel, CustomKernel
from astropy.convolution.kernels import Model1DKernel
from astropy.modeling import Fittable1DModel
import numpy as np
from scipy import ndimage

class SmoothingKernels(Base):
    GAUSSIAN1D = "Gaussian"
    Box1D = "Box"
    MEDIAN = "Median"
    MEAN = "Mean"
    CUSTOM = "Custom"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        methods = {func for func in dir(SmoothingKernels) if callable(getattr(SmoothingKernels, func))}
        return [v for k,v in SmoothingKernels.__dict__.items() if k not in methods and not k.startswith('__')]

smoothing_kernels_list = SmoothingKernels.get_list()
default_smoothing_kernels = [SmoothingKernels.GAUSSIAN1D, SmoothingKernels.Box1D, SmoothingKernels.MEDIAN, SmoothingKernels.MEAN]



class Smoother():
    def __init__(self):
        self.kernel_func=Gaussian1DKernel(int(5))
        self.kernel_func_type=SmoothingKernels.GAUSSIAN1D
        self.kernel_width = 5

    def set_smoothing_kernel(self, kernel=None, kernel_width=None, custom_array_kernel=None, custom_kernel_function=None, function_array_size=21):
        #if custom_kernel_array is None and custom_kernel_function is None:

        if custom_array_kernel is not None:
            custom_kernel_array = np.array([i for i in custom_array_kernel])
            self.kernel_func = CustomKernel(custom_kernel_array)
            self.kernel_func_type = SmoothingKernels.CUSTOM

        elif custom_kernel_function is not None:
            if isinstance(custom_kernel_function, Fittable1DModel):
                self.kernel_func = Model1DKernel(custom_kernel_function, x_size=function_array_size)
            else:
                self.kernel_func = custom_kernel_function

            self.kernel_func_type = SmoothingKernels.CUSTOM

        elif kernel in default_smoothing_kernels:
            width = int(kernel_width)
            if kernel == SmoothingKernels.GAUSSIAN1D:
                self.kernel_func = Gaussian1DKernel(width)
            elif kernel == SmoothingKernels.Box1D:
                self.kernel_func = Box1DKernel(width)
            elif kernel == SmoothingKernels.MEDIAN:
                self.kernel_func = ndimage.median_filter
            elif kernel == SmoothingKernels.MEAN:
                self.kernel_func = ndimage.uniform_filter
            else:
                raise Exception("Unsupported smoothing kernel " + str(kernel))
            self.kernel_func_type = kernel
            self.kernel_width = width
        else:
            raise Exception("Problem while setting the smoothing kernel")


    def get_smoothed_flux(self, flux):
        if callable(self.kernel_func):
            smoothed_flux = self.kernel_func(flux, self.kernel_width)
        else:
            smoothed_flux = convolve(flux, self.kernel_func)
        return smoothed_flux