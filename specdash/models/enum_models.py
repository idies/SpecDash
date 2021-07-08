from .base_model import Base
from specdash import catalog_names
from astropy import units as u

def get_member_list(_class):
    methods = {func for func in dir(_class) if callable(getattr(_class, func))}
    return [v for k, v in _class.__dict__.items() if k not in methods and not k.startswith('__')]


class ObjectType(Base):
    GALAXY = 'GALAXY'
    STAR = 'STAR'
    QSO = 'QSO'
    DEFAULT = "DEFAULT"
    UNKNOWN = "UNKNOWN"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        return get_member_list(ObjectType)

class SpectralLineType(Base):
    INSTRINSIC = "INTRINSIC"
    SKY = "SKY"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        return get_member_list(SpectralLineType)


class SpectrumType(Base):
    OBJECT = "OBJECT"
    #OBJECT_PRECURSOR = "OBJECT_PRECURSOR"
    SKY = "SKY"
    MODEL = "MODEL"
    ERROR = "ERROR"
    FIT = "FIT"
    DEFAULT = "DEFAULT"
    SMOOTHED = "SMOOTHED"
    VISIT = "VISIT"
    REGION = "REGION"
    LINE = "LINE"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        return get_member_list(SpectrumType)

class WavelengthUnit(Base):
    ANGSTROM = "angstrom"
    NANOMETER = "nanometer"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        return get_member_list(WavelengthUnit)

    @staticmethod
    def get_astropy_unit(wavelength_unit):
        unit = None
        if wavelength_unit == WavelengthUnit.ANGSTROM:
            unit = u.Unit("AA")
        elif wavelength_unit == WavelengthUnit.NANOMETER:
            unit = u.nm
        else:
            raise Exception("Unit "+ str(wavelength_unit) + " not supported")
        return unit

    @staticmethod
    def from_astropy_unit(wavelength_unit):
        unit = None
        if wavelength_unit == u.Unit("AA"):
            unit = WavelengthUnit.ANGSTROM
        elif wavelength_unit == u.nm:
            unit = WavelengthUnit.NANOMETER
        else:
            raise Exception("Unit "+ str(wavelength_unit) + " not supported")
        return unit


wavelength_units_list = WavelengthUnit.get_list()

class FluxUnit(Base):
    F_nu = "F_nu"
    F_lambda = "F_lambda"
    AB_magnitude = "AB_magnitude"
    Jansky = "Jansky"

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_list():
        return get_member_list(FluxUnit)

    @staticmethod
    def get_astropy_unit(flux_unit):
        unit = None
        if flux_unit == FluxUnit.F_lambda:
            unit = u.Unit("erg cm-2 s-1 AA-1")
        elif flux_unit == FluxUnit.F_nu:
            unit = u.Unit("erg cm-2 s-1 Hz-1")
        elif flux_unit == FluxUnit.AB_magnitude:
            unit = u.ABmag
        elif flux_unit == FluxUnit.Jansky:
            unit = u.astrophys.Jy
        else:
            raise Exception("Unit "+ str(flux_unit) + " not supported")
        return unit

    @staticmethod
    def from_astropy_unit(flux_unit):
        unit = None
        if flux_unit == u.Unit("erg cm-2 s-1 AA-1"):
            unit = FluxUnit.F_lambda
        elif flux_unit == u.Unit("erg cm-2 s-1 Hz-1"):
            unit = FluxUnit.F_nu
        elif flux_unit == u.ABmag:
            unit = FluxUnit.AB_magnitude
        elif flux_unit == u.astrophys.Jy:
            unit = FluxUnit.Jansky
        else:
            raise Exception("Unit "+ str(flux_unit) + " not supported")
        return unit



flux_units_list = FluxUnit.get_list()
