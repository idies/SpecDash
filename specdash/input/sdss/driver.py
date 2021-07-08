from specdash import api_urls
from specdash.input import DataDriver
from specdash.models import data_models as dm
from specdash.models import enum_models as em
import numpy as np
from specdash.flux import fnu_to_flambda
from specdash.models.data_models import Trace, SpectralLine
from specdash import base_data_directories
#import os.path
import os
from specdash.input import load_data_from_file
import astropy
import io
import requests
import json

__all__ = ["FitsDataDriver"]

class FitsDataDriver(DataDriver):


    MASK_BITS = {
        0:'NOPLUG',
        1:'BADTRACE',
        2:'BADFLAT',
        3:'BADARC',
        4:'MANYBADCOLUMNS',
        5:'MANYREJECTED',
        6:'LARGESHIFT',
        7:'BADSKYFIBER',
        8:'NEARWHOPPER',
        9:'WHOPPER',
        10:'SMEARIMAGE',
        11:'SMEARHIGHSN',
        12:'SMEARMEDSN',
        16:'NEARBADPIXEL',
        17:'LOWFLAT',
        18:'FULLREJECT',
        19:'PARTIALREJECT',
        20:'SCATTEREDLIGHT',
        21:'CROSSTALK',
        22:'NOSKY',
        23:'BRIGHTSKY',
        24:'NODATA',
        25:'COMBINEREJ',
        26:'BADFLUXFACTOR',
        27:'BADSKYCHI',
        28:'REDMONSTER'
    }



    def __init__(self):
        super().__init__()

    @classmethod
    def get_catalog_name(cls):
        #return "sdss"
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir = dir_path.split("/")[-1]
        return dir

    @classmethod
    def get_spectrum_path(cls, specid):
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + specid + ".fits"
        if os.path.exists(path_to_spec_file):
            return path_to_spec_file
        else:
            return ""

    @classmethod
    def is_file_from_catalog(cls, hdulist):
        # this is a simple check for now
        hdu_names = ["PRIMARY", "COADD", "SPZLINE"]
        hdulist_names = [ hdulist[i].name.upper() for i in range(len(hdulist)) ]
        is_from_catalog = True
        for name in hdu_names:
            if name.upper() not in hdulist_names:
                is_from_catalog = False
        return is_from_catalog

    @classmethod
    def is_specid_from_catalog(cls, specid):
        _specid = specid + ".fits" if not specid.endswith(".fits") else specid
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + _specid
        return os.path.exists(path_to_spec_file)

    @classmethod
    def get_trace_list_from_fits(cls, name, hdulist=None, file_object=None):
        if hdulist is None and file_object is not None:
            hdulist = astropy.io.read(file_object)#(io.BytesIO(decoded_bytes)))
        elif hdulist is None and file_object is None:
            raise Exception("Unspecified parameters hdulist or decoded_bytes")


        if not cls.is_file_from_catalog(hdulist):
            raise Exception("Input spectrum does not belong to sdss catalog")

        catalog_name = cls.get_catalog_name()

        trace_list = []

        coaddData =1 # the index of Coadd data in the HDU list
        zData =3 # index of absorption and emission line data in HDU list
        c=hdulist[coaddData].data
        z=hdulist[zData].data
        prim_header = hdulist[0].header
        if hdulist[2].data['Z'] is not None:
            zlist = hdulist[2].data['Z']
            redshift = [round(z,6) for z in hdulist[2].data['Z']] if type(zlist) == list else [round(float(zlist),6)]
        else:
            redshift = None

        # the name of the data unit can be found on the official SDSS DR webpage

        #note: always convert data types to native python types, not numpy types. The reason is that everything has
        # to be serialized as json, and numpy objects cannot be automatically serialized as such.

        # object spectrum
        trace = Trace()
        trace.name = name
        wavelength = [float(10**lam) for lam in c['loglam']]
        trace.wavelength = wavelength
        trace.wavelength_unit = dm.WavelengthUnit.ANGSTROM
        trace.flux = [1.0*10**-17*float(x) for x in c['flux']]
        trace.flux_error = [1.0*10**-17*np.sqrt(float(1.0/x)) if x != 0 and x != np.nan else None for x in c['ivar']]
        trace.flux_unit = dm.FluxUnit.F_lambda
        trace.flambda = [x for x in trace.flux]
        trace.flambda_error = [x for x in trace.flux_error]

        trace.ancestors = []
        trace.catalog = catalog_name
        trace.spectrum_type = em.SpectrumType.OBJECT
        trace.is_visible = True
        trace.redshift = redshift

        # and its masks:
        mask_info = cls.get_mask_info(trace_name=name, mask_array=[int(m) for m in c['and_mask']], mask_bits=cls.MASK_BITS)
        #trace.masks = {'mask': mask_info.get('mask'), 'mask_values':mask_info.get('mask_values')}
        trace.masks = mask_info
        #trace.mask_bits = mask_info.get('mask_bits')

        # and its metadata
        metadata =  {'catalog':catalog_name, "type":em.SpectrumType.OBJECT, 'ra':str(prim_header["RA"]),'dec':str(prim_header["DEC"]),
                     'mjd':prim_header["MJD"],'plateID':prim_header["PLATEID"],'fiberID':prim_header["FIBERID"]
                    }

        # add redshift values to metadata
        for i in range(len(redshift)):
            metadata['redshift_'+str(i+1)] = str(redshift[i])

        trace.metadata = metadata

        # Loading the sky lines:
        speclines_list = []
        speclines = hdulist[3].data
        for i in range(speclines.size):
            # adding only real lines data:
            if speclines['LINEAREA_ERR'][i] is not None and speclines['LINEAREA_ERR'][i] > 0:
                sline = SpectralLine()
                sline.line = speclines['LINENAME'][i]
                sline.wavelength = speclines['LINEWAVE'][i]
                sline.wavelength_unit = em.WavelengthUnit.ANGSTROM
                sline.flux_unit = em.FluxUnit.F_lambda
                sline.sigma = speclines['LINESIGMA'][i]
                sline.sigma_err = speclines['LINESIGMA_ERR'][i]
                sline.area = speclines['LINEAREA'][i]
                sline.area_err = speclines['LINEAREA_ERR'][i]
                sline.ew = speclines['LINEEW'][i]
                sline.ew_err = speclines['LINEEW_ERR'][i]
                sline.cont_level = speclines['LINECONTLEVEL'][i]
                sline.cont_level_err = speclines['LINECONTLEVEL_ERR'][i]

                speclines_list.append(sline.to_dict())

        trace.spectral_lines = speclines_list

        # append recently-created trace
        trace_list.append(trace)

        # sky spectrum
        sky_trace = Trace()
        sky_trace.catalog = catalog_name
        sky_trace.name = name + "_sky"
        sky_trace.wavelength = wavelength
        sky_trace.flux = [1.0*10**-17*float(x) for x in c['sky']]
        sky_trace.wavelength_unit = dm.WavelengthUnit.ANGSTROM
        sky_trace.flux_unit = dm.FluxUnit.F_lambda
        sky_trace.ancestors = [name]
        sky_trace.flambda = [f for f in sky_trace.flux]
        sky_trace.is_visible = False
        sky_trace.spectrum_type=em.SpectrumType.SKY

        trace_list.append(sky_trace)

        # model trace:

        model_trace = Trace()
        model_trace.catalog = catalog_name
        model_trace.name = name + "_model_1"
        model_trace.spectrum_type_rank = 1
        model_trace.wavelength = wavelength
        model_trace.flux = [1.0*10**-17*float(x) for x in c['model']]
        model_trace.wavelength_unit = dm.WavelengthUnit.ANGSTROM
        model_trace.flux_unit = dm.FluxUnit.F_lambda
        model_trace.ancestors = [name]
        model_trace.flambda = [f for f in model_trace.flux]
        model_trace.is_visible = False
        model_trace.spectrum_type=em.SpectrumType.MODEL

        trace_list.append(model_trace)

        # add visits
        if len(hdulist) > 4:
            for i in range(4,len(hdulist)-1):
                try:
                    visit = Trace()
                    visit.catalog = catalog_name
                    visit.name = name + "_" + hdulist[i].name
                    visit.wavelength = [float(10**lam) for lam in hdulist[i].data['loglam']]
                    visit.flux = [1.0 * 10 ** -17 * float(x) for x in hdulist[i].data['flux']]
                    visit.flux_error = [1.0 * 10 ** -17 * np.sqrt(float(1.0 / x)) if x != 0 and x != np.nan else None for x in hdulist[i].data['ivar']]
                    visit.wavelength_unit = dm.WavelengthUnit.ANGSTROM
                    visit.flux_unit = dm.FluxUnit.F_lambda
                    visit.ancestors = [name]
                    visit.flambda = [f for f in visit.flux]
                    visit.flambda_error = [x for x in visit.flux_error]
                    visit.is_visible = False
                    visit.spectrum_type = em.SpectrumType.VISIT
                    visit.metadata = {'catalog':catalog_name, "type":em.SpectrumType.VISIT, 'id':hdulist[i].name}

                    mask_info = cls.get_mask_info(trace_name=visit.name, mask_array=[int(m) for m in hdulist[i].data['mask']],
                                                  mask_bits=cls.MASK_BITS)
                    visit.masks = mask_info

                    trace_list.append(visit)
                except Exception as ex:
                    pass

        hdulist.close()
        return trace_list

    @classmethod
    def get_data_from_specid(cls, specid, trace_name=None):

        if specid.startswith("spec") or specid.endswith(".fits"):
            specid = specid if specid.endswith(".fits") else specid + ".fits"

            base_dir = base_data_directories[cls.get_catalog_name()]
            run2d_subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(base_dir + "/" + d) is True]
            for run2d_subdir in run2d_subdirs:
                plate = specid.split("-")[1]
                path_to_spec_file = base_dir + run2d_subdir + "/" + plate + "/" + specid
                if not cls.is_safe_path(path_to_spec_file):
                    raise Exception("Invalid specid or file " + specid)
                if os.path.isfile(path_to_spec_file):
                    break

        else:

            #specid = specid if specid.endswith(".fits") else specid + ".fits"
            catalog_name = cls.get_catalog_name()
            url = api_urls[catalog_name] + "?cmd=select+top+1+run2d,plate,mjd,fiberid+from+specobjall+where+specobjid={}&format=json&TaskName=specdash".format(specid)
            response = requests.get(url, timeout=10)
            if response.status_code < 200 & response.status_code >= 300:
                raise Exception("Unable to query input spectrum data")

            dat = json.loads(response.content)
            if type(dat) == dict or len(dat[0]['Rows']) == 0:
                raise Exception("Unable to find " + catalog_name + " spectrum identified by " + str(specid) )

            mjd = dat[0]['Rows'][0]['mjd']
            plate = dat[0]['Rows'][0]['plate']
            fiberid = dat[0]['Rows'][0]['fiberid']
            run2d = dat[0]['Rows'][0]['run2d']

            #path_to_spec_file = base_data_directories[cls.get_catalog_name()] + specid
            spec_file_name = "spec-{:04d}-{}-{:04d}.fits".format(plate,mjd,fiberid)
            path_to_spec_file = base_data_directories[cls.get_catalog_name()] + "{}/{:04d}/{}".format(run2d,plate,spec_file_name)


        if not os.path.isfile(path_to_spec_file):
            raise Exception("Spectrum " + specid + " not found on file system.")


        trace_name = trace_name if trace_name is not None else specid.replace(".fits", "")

        hdulist = astropy.io.fits.open(path_to_spec_file)
        trace_list = cls.get_trace_list_from_fits(trace_name, hdulist=hdulist, file_object=None)
        return (trace_list, None)
