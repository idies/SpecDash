import numpy as np
from .models.enum_models import WavelengthUnit, FluxUnit


#https://en.wikipedia.org/wiki/AB_magnitude

def fnu_to_abmag(fnu):
    if fnu <= 0:
        return None
    else:
        return -2.5 * np.log10(fnu) - 48.60

def fnu_to_flambda(fnu, lam, wavelength_unit):
    if wavelength_unit == WavelengthUnit.NANOMETER:
        lam = lam * 10.0
    return 1.0 / (10 ** -23 * 3.33564095 * 10 ** 4 * (lam) ** 2) * fnu

def fnu_to_jansky(fnu):
    return fnu * 10**23

def flambda_to_fnu(flam, lam, wavelength_unit):
    if wavelength_unit == WavelengthUnit.NANOMETER:
        lam = lam * 10.0
    return 10 ** -23 * 3.33564095 * 10 ** 4 * (lam) ** 2 * flam

def flambda_to_abmag(flam,lam, wavelength_unit):
    return fnu_to_abmag(flambda_to_fnu(flam,lam,wavelength_unit))

def flambda_to_jansky(flam,lam, wavelength_unit):
    return fnu_to_jansky(flambda_to_fnu(flam,lam,wavelength_unit))

def abmag_to_fnu(abmag):
    return 10.0 ** ((abmag + 48.60) / -2.5)

def abmag_to_flambda(abmag,lam, wavelength_unit):
    return fnu_to_flambda(abmag_to_fnu(abmag),lam,wavelength_unit)

def abmag_to_jansky(abmag):
    return fnu_to_jansky(abmag_to_fnu(abmag))

def jansky_to_fnu(jy):
    return jy * 10**-23

def jansky_to_flambda(jy, lam, wavelength_unit):
    return fnu_to_flambda(jansky_to_fnu(jy), lam, wavelength_unit)

def jansky_to_absmag(jy):
    return fnu_to_abmag(jansky_to_fnu(jy))




def convert_flux(flux = [], wavelength = [], from_flux_unit = FluxUnit.F_lambda, to_flux_unit = FluxUnit.F_lambda, to_wavelength_unit=WavelengthUnit.ANGSTROM):

    if from_flux_unit != to_flux_unit and from_flux_unit is not None:
        if from_flux_unit == FluxUnit.F_lambda and to_flux_unit == FluxUnit.F_nu:
            return [flambda_to_fnu(flam, wavelength[i], to_wavelength_unit) if flam is not None else None for (i, flam) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.F_lambda and to_flux_unit == FluxUnit.AB_magnitude:
            return [flambda_to_abmag(flam, wavelength[i], to_wavelength_unit) if flam is not None else None for (i, flam) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.F_lambda and to_flux_unit == FluxUnit.Jansky:
            return [flambda_to_jansky(flam, wavelength[i], to_wavelength_unit) if flam is not None else None for (i, flam) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.F_nu and to_flux_unit == FluxUnit.F_lambda:
            return [fnu_to_flambda(fnu, wavelength[i], to_wavelength_unit) if fnu is not None else None for (i, fnu) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.F_nu and to_flux_unit == FluxUnit.AB_magnitude:
            return [fnu_to_abmag(fnu) if fnu is not None else None for fnu in flux]
        elif from_flux_unit == FluxUnit.F_nu and to_flux_unit == FluxUnit.Jansky:
            return [fnu_to_jansky(fnu) if fnu is not None else None for fnu in flux]
        elif from_flux_unit == FluxUnit.AB_magnitude and to_flux_unit == FluxUnit.F_lambda:
            return [abmag_to_flambda(absmag, wavelength[i], to_wavelength_unit) if absmag is not None else None for (i, absmag) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.AB_magnitude and to_flux_unit == FluxUnit.F_nu:
            return [abmag_to_fnu(absmag) if absmag is not None else None for (i, absmag) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.AB_magnitude and to_flux_unit == FluxUnit.Jansky:
            return [abmag_to_jansky(abmag) if abmag is not None else None for (i, abmag) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.Jansky and to_flux_unit == FluxUnit.F_lambda:
            return [jansky_to_flambda(jy, wavelength[i], to_wavelength_unit) if jy is not None else None for (i, jy) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.Jansky and to_flux_unit == FluxUnit.F_nu:
            return [jansky_to_fnu(jy) if jy is not None else None for (i, jy) in enumerate(flux)]
        elif from_flux_unit == FluxUnit.Jansky and to_flux_unit == FluxUnit.AB_magnitude:
            return [jansky_to_absmag(jy) if jy is not None else None for (i, jy) in enumerate(flux)]
        else:
            raise Exception(
                "Unsupported unit " + str(to_flux_unit) + " . Parameter to_flux_unit takes values from class FluxUnit.")

    else:
        return [x for x in flux]


def convert_wavelength(wavelength, from_wavelength_unit=WavelengthUnit.ANGSTROM, to_wavelength_unit=WavelengthUnit.ANGSTROM):
    if from_wavelength_unit != to_wavelength_unit and to_wavelength_unit is not None:
        if from_wavelength_unit == WavelengthUnit.ANGSTROM and to_wavelength_unit == WavelengthUnit.NANOMETER:
            return [x / 10.0 for x in wavelength]
        elif from_wavelength_unit == WavelengthUnit.NANOMETER and to_wavelength_unit == WavelengthUnit.ANGSTROM:
            return [x * 10.0 for x in wavelength]
        else:
            raise Exception("Unsupported unit " + str(
                to_wavelength_unit) + " . Parameter to_wavelength_unit takes values from class WavelengthUnit.")
    else:
        return [x for x in wavelength]
