from specdash.input import DataDriver
from specdash.models import data_models as dm
from specdash.models import enum_models as em
import numpy as np
from specdash.models.data_models import Trace, RedshiftDistribution, SpectralLine
from specdash import base_data_directories
import os.path
from .pfs.datamodel.drp import PfsObject
from astropy.io import fits
from collections import namedtuple
import specdash.flux as fl

__all__ = ["FitsDataDriver"]


class FitsDataDriver(DataDriver):

    def __init__(self):
        super().__init__()

    @classmethod
    def get_catalog_name(cls):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = dir_path.split("/")[-1]
        return dir_path

    @classmethod
    def get_spectrum_path(cls, specid):
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + specid
        if os.path.exists(path_to_spec_file):
            return path_to_spec_file
        else:
            return ""

    @classmethod
    def is_file_from_catalog(cls, hdulist):
        # this is a simple check for now
        hdu_names = ["PRIMARY", "FLUX", "MASK", "TARGET", "SKY", "COVAR", "COVAR2", "OBSERVATIONS", "FLUX_TABLE"]
        hdulist_names = [hdulist[i].name.upper() for i in range(len(hdulist))]
        is_from_catalog = True
        for name in hdu_names:
            if name.upper() not in hdulist_names:
                is_from_catalog = False
        return is_from_catalog

    @classmethod
    def is_specid_from_catalog(cls, specid):
        _specid = specid if specid.endswith(".fits") else specid + ".fits"
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + "spectra/" + _specid
        return os.path.exists(path_to_spec_file)

    @classmethod
    def get_trace_list_from_fits(cls, name, hdulist=None, file_object=None):
        if file_object is None:
            raise Exception("Unspecified parameter file_object")
        if hdulist is not None and file_object is None:
            raise Exception("Unable to use hdulist to parse file. Use file_object instead.")

        try:
            data = PfsObject.readFits(file_object)
        except Exception as ex:
            raise Exception("Unable to parse input spectrum as pfs object.")

        trace_list = []

        # object spectrum
        trace = Trace()
        trace.name = name
        wavelength = [float(x) for x in data.wavelength]
        trace.wavelength = wavelength
        trace.wavelength_unit = dm.WavelengthUnit.NANOMETER
        trace.flux = [float(x)/10**9 if np.abs(x) != np.inf and x != np.nan else None for x in data.flux]
        trace.flux_unit = dm.FluxUnit.Jansky
        trace.flux_error = [float(x)/10**9 if np.abs(x) != np.inf and x != np.nan else None for x in np.sqrt(data.variance)]

        trace.flambda = fl.convert_flux(flux=trace.flux, wavelength=wavelength,
                               from_flux_unit=dm.FluxUnit.Jansky, to_flux_unit=dm.FluxUnit.F_lambda,
                               to_wavelength_unit=dm.WavelengthUnit.NANOMETER)

        trace.flambda_error = fl.convert_flux(flux=trace.flux_error, wavelength=wavelength,
                               from_flux_unit=dm.FluxUnit.Jansky,   to_flux_unit=dm.FluxUnit.F_lambda,
                               to_wavelength_unit=dm.WavelengthUnit.NANOMETER)

        trace.ancestors = []
        trace.catalog = cls.get_catalog_name()
        trace.spectrum_type = em.SpectrumType.OBJECT
        trace.is_visible = True
        trace.photometry = { k:v for (k,v) in data.target.fiberMags.items()}

        # and its masks:
        mask_bits = { flag:flag_name for  (flag_name,flag) in data.flags.flags.items() }

        mask_info = cls.get_mask_info(trace_name=name, mask_array=[int(m) for m in data.mask], mask_bits=mask_bits)
        trace.masks = mask_info #{'mask': mask_info.get('mask'), 'mask_values':mask_info.get('mask_values')}
        #trace.mask_bits = mask_info.get('mask_bits')

        metadata = { 'catalog':cls.get_catalog_name(), 'type':em.SpectrumType.OBJECT, 'objid':data.target.objId, 'ra':data.target.ra, 'dec':data.target.dec,
                     'tract': data.target.tract, 'targetType':data.target.targetType,'catId':data.target.catId
        }

        trace.metadata = metadata
        trace_list.append(trace)

        # sky spectrum
        sky_trace = Trace()
        sky_trace.catalog = cls.get_catalog_name()
        sky_trace.name = name + "_sky"
        sky_trace.wavelength = wavelength

        sky_trace.flux = [float(x)*10**-17 if np.abs(x) != np.inf and x != np.nan else None for x in data.sky] # original flux is in Flambda
        sky_trace.wavelength_unit = dm.WavelengthUnit.NANOMETER
        sky_trace.flux_unit = dm.FluxUnit.F_lambda
        sky_trace.ancestors = [name]
        sky_trace.flambda = [f for f in sky_trace.flux]
        sky_trace.is_visible = False
        sky_trace.spectrum_type=em.SpectrumType.SKY

        trace_list.append(sky_trace)

        return trace_list


    @classmethod
    def get_data_from_specid(cls, specid, trace_name=None):

        _specid = specid if specid.endswith(".fits") else specid + ".fits"
        trace_name = trace_name if trace_name is not None else specid.replace(".fits","")

        # finding file:
        ids = _specid.split("-")
        relative_path = "pfsObject/" + str(int(ids[1])) + "/" + str(int(ids[2])) + "/" + ids[3] + "/" + _specid
        path_to_spec_file = base_data_directories[cls.get_catalog_name()] + relative_path
        if not cls.is_safe_path(path_to_spec_file):
            raise Exception("Invalid specid or file " + specid)

        spectrum_list = cls.get_trace_list_from_fits(trace_name, hdulist=None, file_object=path_to_spec_file)
        catalog_name = cls.get_catalog_name()

        redshift_distributions = []

        zcandidate_file = _specid.replace("pfsObject-"+ids[1],"pfsZcandidates-{:05d}".format(int(ids[1])))
        relative_path = "lam1d_output/" + str(int(ids[1])) + "/" + str(int(ids[2])) + "/" + ids[3] + "/data/" + zcandidate_file
        path_to_zcandidate_file = base_data_directories[cls.get_catalog_name()] + relative_path
        if not cls.is_safe_path(path_to_zcandidate_file):
            raise Exception("Invalid path to pfsZcandidates file")

        hdulist = fits.open(path_to_zcandidate_file)
        try: # sometimes there is no candidate calculated
            candidates_data = hdulist[1]
            wavelength_data = hdulist[2]
            distributions_data = hdulist[3]

            redshift_distribution = RedshiftDistribution(redshift_array = [], probability_array = [], redshift_solutions = [], model_names = [], solution_coordinates = [], ancestors = [])
            redshift_distribution.name = specid + "_zdist"
            redshift_distribution.ancestors = [trace_name]
            redshift_distribution.catalog = cls.get_catalog_name()
            redshift_distribution.is_visible = True

            round_decimals = 4

            z_arr = np.round(np.asarray(distributions_data.data["REDSHIFT"]), round_decimals)
            z_array_indexes = set()
            ind_padding = 50
            downsampling_size = 10

            #wavelength = [10.0*w for w in wavelength_data.data["WAVELENGTH"]]
            wavelength = [w for w in wavelength_data.data["WAVELENGTH"]]
            for i in range(len(candidates_data.data["MODELFLUX"])):

                # load models for each redshift solution
                model_trace = Trace()
                model_trace.catalog = catalog_name
                model_name = trace_name + "_model_" + str(i+1)  # starts with 1st, 2nd, etc
                model_trace.name = model_name
                model_trace.inner_type_rank = i+1
                model_trace.wavelength = wavelength
                model_trace.wavelength_unit = dm.WavelengthUnit.NANOMETER
                model_trace.flux = [ float(f)/10**9 for f in candidates_data.data["MODELFLUX"][i,:] ]
                model_trace.flux_unit = dm.FluxUnit.Jansky
                model_trace.ancestors = [trace_name]
                model_trace.flambda = fl.convert_flux(flux=model_trace.flux, wavelength=wavelength,
                                                   from_flux_unit=dm.FluxUnit.Jansky, to_flux_unit=dm.FluxUnit.F_lambda,
                                                   to_wavelength_unit=dm.WavelengthUnit.NANOMETER)
                model_trace.is_visible = False
                model_trace.spectrum_type = em.SpectrumType.MODEL
                spectrum_list.append(model_trace)

                # load values for redshift distribution object:

                redshift_solution_value = np.round(candidates_data.data["Z"][i],round_decimals)


                ind = np.argwhere(z_arr == redshift_solution_value)[0][0]
                for i in range(max(0,ind-ind_padding),min(len(z_arr),ind+ind_padding)):
                    z_array_indexes.add(i)

                pdf_solution_value = float(np.exp(np.max(np.asarray(distributions_data.data["PDF"])[ind])))
                redshift_solution_value = float(redshift_solution_value)

                redshift_distribution.redshift_solutions.append(redshift_solution_value)
                redshift_distribution.solution_coordinates.append([redshift_solution_value,pdf_solution_value])
                redshift_distribution.model_names.append(model_name)


            redshift_distribution.redshift_array = [float(x) for i,x in enumerate(distributions_data.data["REDSHIFT"]) if i in z_array_indexes or i % downsampling_size == 0]
            redshift_distribution.probability_array = [float( np.exp(x) ) for i,x in enumerate(distributions_data.data["PDF"])  if i in z_array_indexes or i % downsampling_size == 0]

            redshift_distributions.append(redshift_distribution)

            # adding redshift solution values to object spectrum

            object_spectrum = spectrum_list[0]
            object_spectrum.redshift = redshift_distribution.redshift_solutions
            for i in range(len(redshift_distribution.redshift_solutions)):
                object_spectrum.metadata['redshift_'+str(i+1)] = redshift_distribution.redshift_solutions[i]

            # adding the measured spectral lines:
            # Loading the sky lines:
            speclines_list = []
            speclines = hdulist[4].data
            for i in range(speclines.size):
                sline = SpectralLine()
                sline.line = speclines['LINENAME'][i]
                sline.wavelength = speclines['LINEWAVE'][i]
                sline.wavelength_unit = em.WavelengthUnit.ANGSTROM
                sline.flux_unit = em.FluxUnit.F_lambda
                sline.sigma = speclines['LINESIGMA'][i]
                sline.sigma_err = speclines['LINESIGMA_ERR'][i]
                sline.area = speclines['LINEFLUX'][i]
                sline.area_err = speclines['LINEFLUX_ERR'][i]
                sline.ew = speclines['LINEEW'][i]
                sline.ew_err = speclines['LINEEW_ERR'][i]
                sline.cont_level = speclines['LINECONTLEVEL'][i]
                sline.cont_level_err = speclines['LINECONTLEVEL_ERR'][i]
                speclines_list.append(sline.to_dict())

            object_spectrum.spectral_lines = speclines_list

            # replace updated object spectrum in original list
            spectrum_list[0] = object_spectrum

        except Exception as e:
            pass

        hdulist.close()

        # add visits:
        visits_array = cls.get_visits(trace_name,file_object=path_to_spec_file)
        for visit in visits_array:
            spectrum_list.append(visit)


        return (spectrum_list, redshift_distributions)


    @classmethod
    def get_visits(cls, trace_name, hdulist=None, file_object=None):
        return []

    @classmethod
    def get_visits2(cls, trace_name, hdulist=None, file_object=None):
        if hdulist is not None and file_object is None:
            raise Exception("Unable to use hdulist to parse file. Use file_object instead.")

        path_to_arm_files = base_data_directories[cls.get_catalog_name()] + "arm/fits/"
        visitIDs_array = []

        data = PfsObject.readFits(file_object)  # io.BytesIO(decoded_bytes))
        mask_bits = { flag:flag_name for  (flag_name,flag) in data.flags.flags.items() }
        VisitIDs = namedtuple('VisitIDs', ['visit', 'arm', 'spectrograph', 'fiber'])

        for i in range(data.observations.num):
            visitIDs = VisitIDs(visit=data.observations.visit[i], arm=data.observations.arm[i],
                                            spectrograph=data.observations.spectrograph[i],
                                            fiber=data.observations.fiberId[i])
            visitIDs_array.append(visitIDs)

        # for now:
        visitIDs_array = [VisitIDs(47,'b',1,10),VisitIDs(47,'r',1,11),VisitIDs(47,'n',1,12)]


        visits_array = [ ]
        for visitIDs in visitIDs_array:
            arm_file = "pfsArm-{:06d}-{}{}.fits".format(visitIDs.visit,visitIDs.arm,visitIDs.spectrograph)
            with fits.open(path_to_arm_files+arm_file) as armhdulist:
                name = trace_name + "_arm-{:06d}-{}{}_fiber={}".format(visitIDs.visit,visitIDs.arm,visitIDs.spectrograph,visitIDs.fiber)
                visit = Trace()
                visit.name = name
                visit.ancestors = [trace_name]
                visit.catalog = cls.get_catalog_name()
                visit.spectrum_type = em.SpectrumType.VISIT
                visit.wavelength = [float(10.0 * x) for x in armhdulist[2].data[visitIDs.fiber-1,:]]
                visit.wavelength_unit = dm.WavelengthUnit.ANGSTROM
                visit.flux = [float(x) if np.abs(x) != np.inf and x != np.nan else None for x in armhdulist[3].data[visitIDs.fiber-1,:]]
                visit.flux_error = [float(x) if np.abs(x) != np.inf and x != np.nan else None for x in np.sqrt(armhdulist[6].data[visitIDs.fiber-1, 0, :])]
                visit.flux_unit = dm.FluxUnit.F_lambda
                visit.flambda = [x for x in visit.flux]
                visit.metadata = {'catalog':cls.get_catalog_name(), 'type':em.SpectrumType.VISIT, 'visit':visitIDs.visit,'arm':visitIDs.arm,'spectrograph':visitIDs.spectrograph,'fiberId':visitIDs.fiber}
                visit.is_visible = False

                # and its masks:
                mask_info = cls.get_mask_info(trace_name=name, mask_array=[int(m) for m in armhdulist[4].data[visitIDs.fiber-1, :] ], mask_bits=mask_bits)
                visit.masks = mask_info

                visits_array.append(visit)

        return visits_array
