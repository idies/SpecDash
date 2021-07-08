from collections import OrderedDict
from enum import Enum
from .base_model import Base
from specdash import flux as fl
from .enum_models import WavelengthUnit, FluxUnit, SpectrumType, ObjectType

class Photometry(Base):
    def __init__(self, bands={}):
        self.bands = bands

class Metadata(Base):
    def __init__(self, object_name=None, specid=None, file_path=None, catalog=None, photometry=Photometry(), misc={}):

        super().__init__()
        self.object_name = object_name
        self.specid = specid
        self.file_path = file_path
        self.catalog = catalog
        self.photometry = photometry
        self.misc = misc

class RedshiftDistribution(Base):
    def __init__(self, name="", redshift_array=[], probability_array=[], redshift_solutions=[], model_names=[], solution_coordinates=[], ancestors = [], catalog=None, is_visible=True, color="black", linewidth=1, alpha=1):

        super().__init__()
        self.name = name
        self.redshift_array = redshift_array
        self.probability_array = probability_array
        self.color=color
        self.linewidth=linewidth
        self.alpha=alpha
        self.redshift_solutions = redshift_solutions
        self.model_names = model_names
        self.solution_coordinates = solution_coordinates
        self.ancestors = ancestors
        self.catalog = catalog
        self.is_visible = is_visible

class Spectrum(Base):
    def __init__(self,name="", wavelength=[], flux=[], flux_error=[], masks=[], spectral_lines = [],
                 mask_bits={}, wavelength_unit=WavelengthUnit.ANGSTROM, flux_unit=FluxUnit.F_lambda,
                 catalog=None, spectrum_type=SpectrumType.OBJECT, redshift=None, color="rgb(0,0,0)", linewidth=1, alpha=1):

        Base.__init__(self)

        if wavelength_unit not in WavelengthUnit.get_list():
            raise Exception("Parameter wavelength_unit must take a value from WavelengthUnit class: " + str(WavelengthUnit.get_list()))

        if flux_unit not in FluxUnit.get_list():
            raise Exception("Parameter flux_unit must take a value from FluxUnit class: " + str(FluxUnit.get_list()))

        self.name = name
        self.wavelength = [x for x in wavelength]
        self.flux = [x for x in flux]
        self.flux_error = [x for x in flux_error]
        self.masks = masks
        self.spectral_lines = spectral_lines
        self.mask_bits = mask_bits
        self.wavelength_unit = wavelength_unit
        self.flux_unit = flux_unit
        self.catalog = catalog
        self.spectrum_type = spectrum_type
        self.color = color,
        self.linewidth = linewidth,
        self.alpha = alpha
        self.redshift = redshift

        def from_spectrum1d(self, spectrum1d, name, is_visible = True):
            self.name = name
            self.redshift = float(spectrum1d.redshift.value)
            self.flambda = fl.convert_flux([x for x in spectrum1d.flux], [x for x in spectrum1d.wavelength], spectrum1d.flux_unit, FluxUnit.F_lambda, WavelengthUnit.ANGSTROM)
            self.is_visible = is_visible


class Trace(Spectrum):
    def __init__(self,name="", wavelength=[], flux=[], flux_error=[], masks={}, spectral_lines = [],
                 mask_bits={}, wavelength_unit=WavelengthUnit.ANGSTROM, flux_unit=FluxUnit.F_lambda,
                 catalog=None, spectrum_type=SpectrumType.OBJECT, redshift=None, color="rgb(0,0,0)", linewidth=1, alpha=1,
                 inner_type_rank=1, flambda=[], flambda_error=[], is_visible=True, show_error=False, ancestors=[], photometry={}, metadata={}, wavelength_boundaries=[]):

        Spectrum.__init__(self, name, wavelength, flux, flux_error, masks, spectral_lines, mask_bits, wavelength_unit, flux_unit, catalog, spectrum_type, redshift, color, linewidth, alpha)
        self.inner_type_rank = inner_type_rank
        self.flambda = [x for x in flambda]
        self.flambda_error = [x for x in flambda_error]
        self.is_visible = is_visible
        self.show_error = show_error
        self.ancestors = ancestors
        self.photometry = photometry
        self.metadata = metadata
        self.wavelength_boundaries = wavelength_boundaries

    def from_spectrum(self, spectrum, ancestors=[], is_visible = True):
        for key,value in spectrum.to_dict().items():
            self.__dict__[key] = value

        self.flambda = fl.convert_flux(spectrum.flux, spectrum.wavelength, spectrum.flux_unit, FluxUnit.F_lambda, WavelengthUnit.ANGSTROM)
        self.is_visible = is_visible
        self.ancestors = ancestors

    def to_spectrum(self):
        return Spectrum().from_dict(self.__dict__)


class SpectralLine(Base):
    def __init__(self, line=None, wavelength=None, wavelength_unit=None, flux_unit=None,
                 sigma=None, sigma_err=None, area = None, area_err=None,
                 ew=None, ew_err=None, cont_level=None, cont_level_err=None):

        Base.__init__(self)

        self.line = line
        self.wavelength = wavelength
        self.wavelength_unit = wavelength_unit
        self.flux_unit = flux_unit
        self.sigma = sigma
        self.sigma_err = sigma_err
        self.area = area,
        self.area_err = area_err,
        self.ew = ew
        self.ew_err = ew_err
        self.cont_level = cont_level
        self.cont_level_err = cont_level_err


class SpectrumLine:
    def __init__(self, lambda1=None, lambda2=None, name=None, medium=None, color="lightblue", linewidth=1, alpha=0.3):
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.name = name
        if medium is None:
            medium = Medium.AIR
        self.medium = medium
        self.color = color
        self.linewidth = linewidth
        self.alpha = alpha


class Medium(Enum):
        AIR = 1
        VACUUM = 2

class SpectrumLineGrid:
    def __init__(self, spectrum_line_grid=None):
        if spectrum_line_grid is None:
            self.grid = OrderedDict()
        else:
            self.grid = spectrum_line_grid

    def add_line(self, spectrum_line, spectrum_line_name):
        self.grid[spectrum_line_name] = spectrum_line

    def remove_line(self, spectrum_line_name):
        self.grid.pop(spectrum_line_name)


def getter_setter_gen(name, type_):
    def getter(self):
        return getattr(self, "__" + name)
    def setter(self, value):
        if not isinstance(value, type_):
            raise TypeError("%s attribute must be set to an instance of %s" % (name, type_))
        setattr(self, "__" + name, value)
    return property(getter, setter)

def auto_attr_check(cls):
    new_dct = {}
    for key, value in cls.__dict__.items():
        if isinstance(value, type):
            value = getter_setter_gen(key, value)
        new_dct[key] = value
    # Creates a new class, using the modified dictionary as the class dict:
    return type(cls)(cls.__name__, cls.__bases__, new_dct)
