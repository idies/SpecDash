from abc import ABC, abstractmethod
from specdash import base_data_directories

import sys, os
import importlib
import astropy
import io
import uuid

def get_supported_catalogs():
    input_drivers = _get_input_drivers()
    catalog_names = [ input_driver.get_catalog_name() for input_driver in input_drivers ]
    return catalog_names

def _get_catalog_directories():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    catalog_dirs = [f for f in os.listdir(dir_path) if not f.startswith("_")][::-1]
    return catalog_dirs

def _get_input_drivers():
    catalog_dirs = _get_catalog_directories()
    input_drivers = [_get_input_driver(catalog_name) for catalog_name in catalog_dirs]
    return input_drivers

def _get_input_driver(catalog_name):
    try:
        if catalog_name not in _get_catalog_directories():
            raise Exception("Catalog "+catalog_name + " not in supported catalogs list: " + str(_get_catalog_directories()))

        input_driver = importlib.import_module("specdash.input."+catalog_name).driver.FitsDataDriver
        return input_driver
    except Exception as ex:
        catalog_dirs = get_supported_catalogs()
        #raise Exception("Could not find suitable driver for reading the input file(s). \
        #                Current drivers list available for " + str(catalog_dirs))
        raise ex

def load_data_from_file(trace_name, catalog_name, decoded_bytes=None, file_path=None):
    if trace_name == "" and decoded_bytes is not None:
        raise Exception("Unspecified argument trace_name")

    if decoded_bytes is not None:
        file_object = io.BytesIO(decoded_bytes)
        hdulist = astropy.io.fits.open(io.BytesIO(decoded_bytes))
    elif file_path is not None:
        file_object = file_path
        hdulist = astropy.io.fits.open(file_path)
    else:
        raise Exception("Unspecified arguments decoded_bytes or file_path")

    fits_input_driver =  _get_input_driver(catalog_name)
    return fits_input_driver.get_trace_list_from_fits(trace_name, hdulist=hdulist, file_object=file_object)

def load_data_from_specid(specid, trace_name=None, catalog_name=None):

    if trace_name == "":
        raise Exception("Name of spectrum cannot be the empty string")

    if catalog_name is not None and catalog_name != "":
        input_driver = _get_input_driver(catalog_name)
        return input_driver.get_data_from_specid(specid, trace_name)
    else:
        input_drivers = _get_input_drivers()
        for input_driver in input_drivers:
            if input_driver.is_specid_from_catalog(specid):
                return input_driver.get_data_from_specid(specid, trace_name)
        catalog_dirs = get_supported_catalogs()
        raise Exception("Could not find suitable driver for reading the input specid, or specid does not exist in supported catalogs. Current drivers available for "+str(catalog_dirs))



def get_spectrum_path(specid):
    input_drivers = _get_input_drivers()
    catalog_dirs = get_supported_catalogs()
    for fits_driver in input_drivers:
        path = fits_driver.get_spectrum_path(specid)
        if path is not None and path is not False and path != "" :
            return path
    raise Exception("specid can't be found with current drivers. Current drivers list available for "+str(catalog_dirs))


class DataDriver(ABC):

    def __init__(self):
        super().__init__()

    @classmethod
    def get_base_data_directory(cls):
        catalog_name = cls.get_catalog_name()
        return base_data_directories.get(catalog_name, None)

    @classmethod
    def _get_mask_id(cls, catalog_or_file_name, mask_name, bit):
        #return str(catalog_or_file_name) + " " + str(mask_name) + " " + str(bit)
        return str(uuid.uuid1())

    @classmethod
    def _parse_mask(cls, mask_array):

        mask = {}
        mask_value = mask_array[0]
        mask[mask_value] = [[0, 0]]
        unique_mask_values = set()

        for i in range(1, len(mask_array), 1):
            new_mask_value = mask_array[i]
            unique_mask_values.add(int(new_mask_value))

            if new_mask_value == mask_value:
                mask[mask_value][-1][1] = i
            else:
                if new_mask_value not in mask:
                    mask[new_mask_value] = [[i, i]]
                else:
                    arr = mask[new_mask_value]
                    arr.append([i, i])
                    mask[new_mask_value] = arr

                mask_value = new_mask_value

        return mask, unique_mask_values

    @classmethod
    def get_mask_info(cls, trace_name, mask_array, mask_bits):

        catalog = cls.get_catalog_name()
        mask, unique_mask_values = cls._parse_mask(mask_array)
        bits = {bit for bit in mask_bits for mv in unique_mask_values if (mv & 2 ** bit) != 0}
        mask_values = {cls._get_mask_id(trace_name, bit_name, bit): {'bit': bit, 'catalog': catalog, 'name': bit_name} for (bit,bit_name) in mask_bits.items() if bit in bits}
        return {'mask': mask, 'mask_values': mask_values}

    @classmethod
    @abstractmethod
    def get_spectrum_path(cls, specid) -> str:
        """returns a non empty string if specid is found in file system. Else, returns an empty string or None"""
        pass

    @classmethod
    @abstractmethod
    def is_file_from_catalog(cls, hdulist: list) -> bool:
        """returns True if the file's HDLUList can be identified as belonging to this catalog. False otherwise"""
        pass

    @classmethod
    @abstractmethod
    def is_specid_from_catalog(cls, specid: str) -> bool:
        """returns True if the file's HDLUList can be identified as belonging to this catalog. False otherwise"""
        pass

    @classmethod
    @abstractmethod
    def get_catalog_name(cls) -> str:
        """Gets the name of the catalog which the driver is processing data for. E.g., SDSS"""
        pass

    b='''
    @classmethod
    @abstractmethod
    def get_mask_description_list(cls) -> list:
        """List of mask bit descriptions.
        Each description is in turn a list of the format [mask_name (string), mask_bit (integer), description (string)]"""
        pass
'''

    @classmethod
    @abstractmethod
    def get_trace_list_from_fits(cls, name: str, hdulist: list, file_object: object) -> list:
        pass

    @classmethod
    @abstractmethod
    def get_data_from_specid(cls, specid: str, trace_name:str) -> tuple:
        pass


    @classmethod
    def is_safe_path(cls, path):
        base_dir = cls.get_base_data_directory()
        if os.path.commonprefix((os.path.realpath(path), base_dir)) == base_dir:
            return True
        else:
            return False


def check_base_data_directories():
    catalog_names = get_supported_catalogs()
    for catalog_name in base_data_directories:
        if catalog_name not in catalog_names:
            raise Exception("Catalog '"+catalog_name+"' not found under supported catalogs in list "+str(catalog_names))
        if not os.path.isdir(base_data_directories[catalog_name]):
            raise Exception("Catalog path " + str(base_data_directories[catalog_name]) + " does not exist.")

## need to check them at start up time to check for inconsistencies
check_base_data_directories()
