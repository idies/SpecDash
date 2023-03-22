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
        0:'BADPIX',
        1:'CRPIX',
        2:'SATPIX',
        3:'UNFIXABLE',
        4:'BADDARK',
        5:'BADFLAT',
        6:'BADERR',
        7:'NOSKY',
        8:'LITTROW_GHOST',
        9:'PERSIST_HIGH',
        10:'PERSIST_MED',
        11:'PERSIST_LOW',
        12:'SIG_SKYLINE',
        13:'SIG_TELLURIC',
        14: 'NOT_ENOUGH_PSF',
        15: '',
        16: 'SIG_TELLURIC'
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
        hdu_names = ['PRIMARY', '', '', '', '', '', '', '', '', '', '']
        hdulist_names = [ hdulist[i].name.upper() for i in range(len(hdulist))]
        if hdu_names == hdulist_names:
            return True
        else:
            return False

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

        #coaddData = 1 # the index of Coadd data in the HDU list
        #zData =3 # index of absorption and emission line data in HDU list
        #c=hdulist[coaddData].data
        #z=hdulist[zData].data
        #prim_header = hdulist[0].header
        #if hdulist[2].data['Z'] is not None:
        #    zlist = hdulist[2].data['Z']
        #    redshift = [round(z,6) for z in hdulist[2].data['Z']] if type(zlist) == list else [round(float(zlist),6)]
        #else:
        #    redshift = None

        prim_header = hdulist[0].header
        flux_dat = hdulist[1].data
        err_dat = hdulist[2].data
        mask_dat = hdulist[3].data
        sky_dat = hdulist[5].data
        model_dat = hdulist[5].data

        n_wave = hdulist[0].header['NWAVE']
        start_wl = hdulist[0].header['CRVAL1']
        diff_wl = hdulist[0].header['CDELT1']
        wl_full_log = np.arange(start_wl, diff_wl * n_wave + start_wl, diff_wl)
        wavelength = [10 ** aval for aval in wl_full_log]


        # the name of the data unit can be found on the official SDSS DR webpage

        #note: always convert data types to native python types, not numpy types. The reason is that everything has
        # to be serialized as json, and numpy objects cannot be automatically serialized as such.

        # object spectrum
        trace = Trace()
        trace.name = name
        trace.wavelength = wavelength
        trace.wavelength_unit = dm.WavelengthUnit.ANGSTROM
        trace.flux = [x if x != 0 and x != np.nan else None for x in flux_dat[0,:]]
        trace.flux_error = [x if x != 0 and x != np.nan else None for x in err_dat[0,:]]
        trace.flux_unit = dm.FluxUnit.F_lambda
        trace.flambda = [x for x in trace.flux]
        trace.flambda_error = [x for x in trace.flux_error]

        trace.ancestors = []
        trace.catalog = catalog_name
        trace.spectrum_type = em.SpectrumType.OBJECT
        trace.is_visible = True
        trace.redshift = 0

        # and its masks:
        mask_info = cls.get_mask_info(trace_name=name, mask_array=[int(m) for m in mask_dat[0,:]], mask_bits=cls.MASK_BITS)
        #trace.masks = {'mask': mask_info.get('mask'), 'mask_values':mask_info.get('mask_values')}
        trace.masks = mask_info
        #trace.mask_bits = mask_info.get('mask_bits')

        # and its metadata
        # https://data.sdss.org/datamodel/files/APOGEE_REDUX/APRED_VERS/stars/TELESCOPE/FIELD/apStar.html#hdu1
        metadata =  {'catalog':catalog_name, "type": em.SpectrumType.OBJECT, 'ra':str(prim_header["RA"]),'dec':str(prim_header["DEC"]),
                     'glon': str(prim_header["GLON"]), 'glat': str(prim_header["GLAT"]),
                     'vrad': prim_header["VRAD1"], 'vhelio': prim_header["VHELIO1"],
                     'J_mag':prim_header["J"],'H_mag':prim_header["H"],'K_mag':prim_header["K"]
                    }
        trace.metadata = metadata

        # append recently-created tracel
        trace_list.append(trace)

        # sky spectrum
        sky_trace = Trace()
        sky_trace.catalog = catalog_name
        sky_trace.name = name + "_sky"
        sky_trace.wavelength = wavelength
        sky_trace.flux = [x if x != 0 and x != np.nan else None for x in sky_dat[0,:]]
        sky_trace.wavelength_unit = dm.WavelengthUnit.ANGSTROM
        sky_trace.flux_unit = dm.FluxUnit.F_lambda
        sky_trace.ancestors = [name]
        sky_trace.flambda = [f for f in sky_trace.flux]
        sky_trace.is_visible = False
        sky_trace.spectrum_type=em.SpectrumType.SKY

        trace_list.append(sky_trace)


        hdulist.close()
        return trace_list

    @classmethod
    def get_data_from_specid(cls, specid, trace_name=None):

        catalog_name = cls.get_catalog_name()
        url = api_urls[catalog_name] + "?query=LoadExplore&format=json&apid={}".format(specid)
        response = requests.get(url, timeout=10)
        if response.status_code < 200 & response.status_code >= 300:
            raise Exception("Unable to query input spectrum data")

        dat = json.loads(response.content)
        if type(dat) == dict or len(dat[0]['Rows']) == 0:
            raise Exception("Unable to find " + catalog_name + " spectrum identified by " + str(specid) )

        apstar_id = dat[12]['Rows'][0]['apstar_id']
        field_name = dat[12]['Rows'][0]['field_name']
        spec_file_name = dat[12]['Rows'][0]['file']
        data_release = f"dr{dat[0]['Rows'][0]['release']}"
        telescope = apstar_id.split('.')[1]
        sub_path = f"{data_release}/apogee/spectro/redux/{data_release}/stars/{telescope}/{field_name}/{spec_file_name}"
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + sub_path

        if not os.path.isfile(path_to_spec_file):
            path_to_spec_file = f"https://{data_release}.sdss.org/sas/{data_release}/prior-surveys/sdss4-dr17-apogee2/spectro/redux/dr17/stars/{telescope}/{field_name}/{spec_file_name}"

        trace_name = trace_name if trace_name is not None else specid.replace(".fits", "")
        try:
            hdu_list = astropy.io.fits.open(path_to_spec_file)
            trace_list = cls.get_trace_list_from_fits(trace_name, hdulist=hdu_list, file_object=None)
            return trace_list, None
        except Exception as e:
            raise Exception("Could not retrieve spectrum '" + specid + "' from file system or from the SAS.")

