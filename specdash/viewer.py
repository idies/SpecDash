import flask
from flask_caching import Cache
from flask_socketio import SocketIO
from jupyter_dash import JupyterDash
from jupyter_dash.comms import _send_jupyter_config_comm_request
from specdash import base_logs_directory, external_stylesheets, external_scripts, port, do_log, max_num_traces
import numpy as np
from specdash import app_layout, callbacks
from datetime import datetime
import json
import multiprocessing
import base64
from .models.enum_models import WavelengthUnit, FluxUnit, SpectrumType
from .models.data_models import Trace, Spectrum, SpectralLine
from specdash.colors import get_next_color
import specdash.flux as fl
from specdash import input
from specdash.utilities import get_specid_list, get_unused_port
from .smoothing.smoother import Smoother, default_smoothing_kernels, SmoothingKernels
from .fitting.fitter import ModelFitter, default_fitting_models, FittingModels
from specutils import Spectrum1D, analysis, fitting, manipulation, SpectralRegion
import uuid
from dash import no_update
from collections import OrderedDict
from pathlib import Path
import os

process_manager = multiprocessing.Manager()

class Viewer():
    """
    Class representing the spectrum viewer object.
    """

    _APP_DATA_KEYS_ = ["traces", "fitted_models", "selection", "smoothing_kernel_types", "fitting_model_types",
                     "redshift_distributions", "metadata", "line_analysis", 'axis_units', "updates",
                     'trace_store_mapping', 'zdist_store_mapping']

    def __init__(self, as_website=False):
        """
        Instantiates the viewer class, depending on whether it will run as a stand alone website or inside Jupyter.
        :param as_website: boolean
            Set as True if the viewer is intended to run as a stand alone website. and set to False if not (i.e., runs inside Jupyter)
        """
        self.as_website = as_website
        self.app_port = get_unused_port(initial_port=port)
        self.as_website = as_website

        if not self.as_website:
            _send_jupyter_config_comm_request()
            JupyterDash.infer_jupyter_proxy_config()
            assets_ignore = ""
        else:
            assets_ignore = "websocket.js"

        self.server = flask.Flask(__name__)  # define flask app.server
        self.app = JupyterDash(__name__, external_stylesheets=external_stylesheets, external_scripts=external_scripts,
                               server=self.server, assets_ignore=assets_ignore, suppress_callback_exceptions=True)

        if not as_website:
            self.socketio = SocketIO(self.server, async_mode="threading", logger=False, engineio_logger=False)

        self.app.server.secret_key = 'SOME_KEY_STRING'
        self.app.title = "SpecDash"
        self._initialize_app_data()
        self.app_data_timestamp['timestamp'] = 0
        self.debug_data = process_manager.dict()
        self.smoother = Smoother()
        self.model_fitter = ModelFitter()
        self.storage_mode = "memory" if as_website else "memory"
        self.app.layout = self._get_app_layout
        session_id = str(uuid.uuid4())
        callbacks.load_callbacks(self)
        self._initialize_api_endpoints()

    def _initialize_api_endpoints(self):
        @self.server.route('/api/health')
        def health():
            return {'is_healthy': True}

    def _initialize_app_data(self):
        self.app_data = process_manager.dict()
        self.app_data_timestamp = process_manager.dict()
        for key, value in Viewer._build_app_data().items():
            self.app_data[key] = value

        self._initialize_updates(self.app_data)

    @staticmethod
    def _initialize_updates(app_data):
        _updates = {}
        _updates["updated_traces"] = []
        _updates["removed_traces"] = []
        _updates["added_traces"] = []

        _updates["updated_zdists"] = []
        _updates["removed_zdists"] = []
        _updates["added_zdists"] = []

        app_data["updates"] = _updates

    @staticmethod
    def _set_trace_updates_info(app_data, added_trace_names=[], removed_trace_names=[], updated_trace_names=[],
                                added_zdist_names=[], removed_zdist_names=[], updated_zdist_names=[]):
        if len(app_data['traces']) > max_num_traces or len(app_data['redshift_distributions']) > max_num_traces:
            raise Exception("Maximum number of loaded traces exceeded")

        _updates = app_data["updates"]
        _added_traces = _updates["added_traces"] + [name for name in added_trace_names]
        _updates["added_traces"] = list(OrderedDict.fromkeys(_added_traces))
        _removed_traces = _updates["removed_traces"] + [name for name in removed_trace_names]
        _updates["removed_traces"] = list(OrderedDict.fromkeys(_removed_traces))
        _updated_traces = _updates["updated_traces"] + [name for name in updated_trace_names]
        _updates["updated_traces"] = list(OrderedDict.fromkeys(_updated_traces))

        _added_zdists = _updates["added_zdists"] + [name for name in added_zdist_names]
        _updates["added_zdists"] = list(OrderedDict.fromkeys(_added_zdists))
        _removed_zdists = _updates["removed_zdists"] + [name for name in removed_zdist_names]
        _updates["removed_zdists"] = list(OrderedDict.fromkeys(_removed_zdists))
        _updated_zdists = _updates["updated_zdists"] + [name for name in updated_zdist_names]
        _updates["updated_zdists"] = list(OrderedDict.fromkeys(_updated_zdists))

        app_data["updates"] = _updates

    @staticmethod
    def _build_trace_store_mapping(app_data):
        if len(app_data['trace_store_mapping']) == 0:
            trace_store_mapping = app_data['trace_store_mapping']
            for index, trace_name in enumerate(app_data['traces']):
                trace_store_mapping[trace_name] = index
            app_data['trace_store_mapping'] = trace_store_mapping

    @staticmethod
    def _build_zdist_store_mapping(app_data):
        if len(app_data['zdist_store_mapping']) == 0:
            zdist_store_mapping = app_data['zdist_store_mapping']
            for index, zdist_name in enumerate(app_data['redshift_distributions']):
                zdist_store_mapping[zdist_name] = index
            app_data['zdist_store_mapping'] = zdist_store_mapping

    @staticmethod
    def _get_returned_store_traces(app_data):
        returned_store_traces = [no_update for i in range(max_num_traces)]
        for name in app_data["updates"]["updated_traces"]:
            i = app_data["trace_store_mapping"][name]
            returned_store_traces[i] = app_data["traces"][name]
        trace_store_mapping = app_data["trace_store_mapping"]
        for name in app_data["updates"]["removed_traces"]:
            i = app_data["trace_store_mapping"][name]
            returned_store_traces[i] = None
            trace_store_mapping.pop(name, None)
        for name in app_data["updates"]["added_traces"]:
            found = False
            for i in range(max_num_traces):
                if not found and i not in trace_store_mapping.values():
                    returned_store_traces[i] = app_data["traces"][name]
                    trace_store_mapping[name] = i
                    found = True
        app_data["trace_store_mapping"] = trace_store_mapping
        return returned_store_traces

    @staticmethod
    def _get_returned_store_zdists(app_data):
        returned_store_zdists = [no_update for i in range(max_num_traces)]
        for name in app_data['updates']["updated_zdists"]:
            i = app_data["zdist_store_mapping"][name]
            returned_store_zdists[i] = app_data["redshift_distributions"][name]
        zdist_store_mapping = app_data["zdist_store_mapping"]
        for name in app_data["updates"]["removed_zdists"]:
            i = app_data["zdist_store_mapping"][name]
            returned_store_zdists[i] = None
            zdist_store_mapping.pop(name, None)
        for name in app_data['updates']["added_zdists"]:
            found = False
            for i in range(max_num_traces):
                if not found and i not in app_data["zdist_store_mapping"].values():
                    returned_store_zdists[i] = app_data["redshift_distributions"][name]
                    zdist_store_mapping[name] = i
                    found = True
        app_data["zdist_store_mapping"] = zdist_store_mapping
        return returned_store_zdists

    def _get_app_layout(self):
        return app_layout.load_app_layout(self=self)

    def show_jupyter_app(self, debug=False, mode='jupyterlab'):
        """
        Opens the Spectrum Viewer inside Jupyter.
        :param debug: Boolean, defining whether to include debug functionality.
        :param mode: String defining the opening mode. If set to "jupyterlab", then the viewer opens on a separate tab
        within JupyterLab. If set to "inline", the app will open under the notebook cell. If set to "external",
        the app can be accessed by itself on a separate browser tab.

        :return:
        """
        if not self.as_website:
            self._initialize_app_data()
            self.app.run_server(mode=mode, port=self.app_port, debug=debug, dev_tools_ui=True,
                                dev_tools_props_check=True, dev_tools_hot_reload=True,
                                dev_tools_silence_routes_logging=True)  # dash + jupyterdash

    @staticmethod
    def _build_app_data():
        app_data = {}
        for key in Viewer._APP_DATA_KEYS_:
            # app_data[key] = {}
            app_data[key] = OrderedDict()

        # initialize smoothing kernels with the list of default names
        app_data["smoothing_kernel_types"] = default_smoothing_kernels
        app_data['fitting_model_types'] = default_fitting_models
        app_data['traces'] = OrderedDict()
        app_data['trace_store_mapping'] = OrderedDict()
        Viewer._initialize_updates(app_data)
        Viewer._set_trace_updates_info(app_data)

        return app_data

    @staticmethod
    def _build_graph_settings(axis_units_changed=False):
        graph_settings = {'axis_units_changed': axis_units_changed}
        return graph_settings

    def _parse_uploaded_file(self, contents, file_name, catalog_name, wavelength_unit=WavelengthUnit.ANGSTROM,
                             flux_unit=FluxUnit.F_lambda):

        content_type, content_string = contents.split(',')
        decoded_bytes = base64.b64decode(content_string)

        if "." in file_name:
            file_name_parts = file_name.split(".")
            file_name = ".".join(file_name_parts[:(len(file_name_parts) - 1)])

        return self._load_from_file(trace_name=file_name, catalog_name=catalog_name, decoded_bytes=decoded_bytes,
                                    file_path=None, wavelength_unit=wavelength_unit, flux_unit=flux_unit)

    def _load_from_specid_text(self, specid_text, wavelength_unit, flux_unit, data_dict, catalog_name,
                               do_update_client=False):
        specid_list = get_specid_list(specid_text)
        self._load_from_specid([s for s in specid_list], [s for s in specid_list], wavelength_unit, flux_unit,
                               data_dict, catalog_name, do_update_client=False)
        if do_update_client:
            self._update_client()

    def _set_axis_units(self, data_dict, wavelength_unit, flux_unit):
        if wavelength_unit is not None and flux_unit is not None:
            axis_units = data_dict['axis_units']
            axis_units['wavelength_unit'] = str(wavelength_unit)
            axis_units['flux_unit'] = str(flux_unit)
            data_dict['axis_units'] = axis_units

    def _load_from_specid(self, specid_list, trace_name_list, wavelength_unit, flux_unit, data_dict, catalog_name,
                          do_update_client=False):

        for ind, specid in enumerate(specid_list):
            (spectrum_list, redshift_distributions) = input.load_data_from_specid(specid_list[ind], trace_name_list[ind],
                                                                                  catalog_name)

            rescaled_traces = []
            if wavelength_unit is None and len(spectrum_list) > 0:
                wavelength_unit = spectrum_list[0].wavelength_unit
            if flux_unit is None and len(spectrum_list) > 0:
                flux_unit = spectrum_list[0].flux_unit

            added_traces = []
            added_zdists = []
            for i in range(len(spectrum_list)):
                spectrum = spectrum_list[i]
                trace = spectrum.to_dict()
                trace = self._get_rescaled_axis_in_trace(trace, to_wavelength_unit=wavelength_unit,
                                                         to_flux_unit=flux_unit)

                if data_dict['axis_units'].get('wavelength_unit') is None or data_dict['axis_units'].get(
                        'wavelength_unit') is None:
                    self._set_axis_units(data_dict, wavelength_unit, flux_unit)

                added_traces.append(trace)

            self._set_colors_for_new_traces(new_traces=added_traces,
                                            current_trace_colors=self._get_current_colors(data_dict))

            if redshift_distributions is not None and len(redshift_distributions) > 0:
                for i in range(len(spectrum_list)):
                    redshift_distribution = redshift_distributions[0]  # only one zdist for now
                    if added_traces[i].get("name") == redshift_distribution.ancestors[0]:
                        redshift_distribution.color = added_traces[i]['color']
                        added_zdists.append(redshift_distribution.to_dict())

        self._add_trace_to_data(data_dict, added_traces, do_update_client=False)
        self._add_zdist_to_data(data_dict, added_zdists, do_update_client=False)

        if do_update_client:
            self._update_client()

    def _load_from_file(self, trace_name, catalog_name, decoded_bytes=None, file_path=None,
                        wavelength_unit=WavelengthUnit.ANGSTROM, flux_unit=FluxUnit.F_lambda):

        # assumes that spectrum wavelength units are in Armstrong:
        spectrum_list = input.load_data_from_file(trace_name, catalog_name, decoded_bytes, file_path)

        if wavelength_unit is None and len(spectrum_list) > 0:
            wavelength_unit = spectrum_list[0].wavelength_unit
        if flux_unit is None and len(spectrum_list) > 0:
            flux_unit = spectrum_list[0].flux_unit

        rescaled_traces = []
        for spectrum in spectrum_list:
            trace = spectrum.to_dict()
            rescaled_traces.append(self._get_rescaled_axis_in_trace(trace, to_wavelength_unit=wavelength_unit,
                                                                    to_flux_unit=flux_unit))
        return rescaled_traces

    def _add_spectrum_from_file(self, file_path, data_dict, wavelength_unit, flux_unit, catalog_name, trace_name=None,
                                do_update_client=False):
        if trace_name is None:
            file_path_parts = file_path.split("/")
            name_parts = file_path_parts[-1].split(".")
            trace_name = ".".join(name_parts[:(len(name_parts) - 1)])

        rescaled_traces = self._load_from_file(trace_name, catalog_name=catalog_name, decoded_bytes=None,
                                               file_path=file_path, wavelength_unit=wavelength_unit,
                                               flux_unit=flux_unit)

        if wavelength_unit is None and len(rescaled_traces) > 0:
            wavelength_unit = rescaled_traces[0].get('wavelength_unit')
        if flux_unit is None and len(rescaled_traces) > 0:
            flux_unit = rescaled_traces[0].get('flux_unit')

        self._set_axis_units(data_dict, wavelength_unit, flux_unit)

        self._set_colors_for_new_traces(rescaled_traces, self._get_current_colors(data_dict))
        self._add_trace_to_data(data_dict, rescaled_traces, do_update_client=False)

        if do_update_client:
            self._update_client()

    def _get_current_colors(self, application_data):
        current_traces_colors = [application_data['traces'][trace_name]['color'] for trace_name in
                                 application_data['traces']]

        current_traces_colors += [application_data['redshift_distributions'][trace_name]['color'] for trace_name in
                                  application_data['redshift_distributions']]
        return current_traces_colors

    def _set_color_for_new_trace(self, trace, application_data):
        current_traces_colors = self._get_current_colors(application_data)
        new_color = get_next_color(current_traces_colors)
        trace['color'] = new_color

    def _set_colors_for_new_traces(self, new_traces, current_trace_colors):
        new_colors = self._get_colors_for_new_traces(current_trace_colors, num_output_colors=len(new_traces))
        for i in range(len(new_traces)):
            new_traces[i]['color'] = new_colors[i]

    def _get_colors_for_new_traces(self, current_trace_colors, num_output_colors=1):
        # current_trace_colors = self._get_current_colors(application_data)
        new_colors = []
        for i in range(num_output_colors):
            next_color = get_next_color(current_trace_colors + new_colors)
            new_colors.append(next_color)
        return new_colors

    def _synch_data(self, base_data_dict, incomplete_data_dict, do_update_client=False):
        # self.write_info("inc0  start " + str(incomplete_data_dict) + " " + str(base_data_dict))
        for key in Viewer._APP_DATA_KEYS_:
            incomplete_data_dict[key] = base_data_dict[key]
        if do_update_client:
            self._update_client()

    def _add_trace_to_data(self, application_data, trace, do_update_client=False):
        if type(trace) != list:
            _traces = [trace]
        else:
            _traces = trace

        traces = application_data['traces']
        for trace in _traces:
            if trace.get('name') in traces:
                raise Exception("Trace named '" + trace.get('name') + "' already exists.")

        for trace in _traces:
            traces[trace.get('name')] = trace

        application_data['traces'] = traces

        self._set_trace_updates_info(application_data, added_trace_names=[trace.get('name') for trace in _traces])

        if do_update_client:
            self._update_client()

    def _add_zdist_to_data(self, application_data, redshift_distribution, do_update_client=True):
        if type(redshift_distribution) != list:
            _zdists = [redshift_distribution]
        else:
            _zdists = redshift_distribution

        zdists = application_data['redshift_distributions']
        for zdist in _zdists:
            if zdist.get('name') in zdists:
                raise Exception("Redshift distribution named '" + zdist.get('name') + "' already exists.")

        for zdist in _zdists:
            zdists[zdist.get('name')] = zdist

        application_data['redshift_distributions'] = zdists

        self._set_trace_updates_info(application_data, added_zdist_names=[zdist.get('name') for zdist in _zdists])

        if do_update_client:
            self._update_client()

    def _remove_traces(self, trace_names, data_dict, do_update_client=True, also_remove_children=False):

        # add derived traces to be removed: iterate over traces and find the ones whose ancestors are in the 'trace_names'
        _traces_to_remove = [name for name in trace_names]

        for name in data_dict['traces']:
            for ancestor in data_dict['traces'][name]['ancestors']:
                if ancestor in _traces_to_remove:
                    if also_remove_children:
                        # remove all children.
                        _traces_to_remove.append(name)
                    else:
                        # remove only if it is not visible
                        if data_dict['traces'][name]['is_visible'] == False:
                            _traces_to_remove.append(name)

        # remove duplicates
        _traces_to_remove = set(_traces_to_remove)

        traces = data_dict['traces']
        for trace_name in _traces_to_remove:
            traces.pop(trace_name)
        data_dict['traces'] = traces

        self._set_trace_updates_info(data_dict, removed_trace_names=[n for n in _traces_to_remove])

        # delete redshift distributions associated with traces to remove
        _zdists_to_remove = []
        for zdist_name in data_dict['redshift_distributions']:
            for ancestor in data_dict['redshift_distributions'][zdist_name]['ancestors']:
                if ancestor in _traces_to_remove:
                    _zdists_to_remove.append(zdist_name)

        _zdists_to_remove = set(_zdists_to_remove)

        zdists = data_dict['redshift_distributions']
        for zdist_name in _zdists_to_remove:
            zdists.pop(zdist_name)
        data_dict['redshift_distributions'] = zdists
        self._set_trace_updates_info(data_dict, removed_zdist_names=[n for n in _zdists_to_remove])

        # remove fitting models associated with traces to remove
        _fitted_models_to_remove = []
        for fitted_model_name in data_dict['fitted_models']:
            for ancestor in data_dict['fitted_models'][fitted_model_name]['ancestors']:
                if ancestor in _traces_to_remove:
                    _fitted_models_to_remove.append(fitted_model_name)
        _fitted_models_to_remove = set(_fitted_models_to_remove)

        fitted_models = data_dict['fitted_models']
        for fitted_model_name in _fitted_models_to_remove:
            fitted_models.pop(fitted_model_name)
        data_dict['fitted_models'] = fitted_models

        if do_update_client:
            self._update_client()

    def _toggle_derived_traces(self, derived_trace_type, ancestor_trace_names, data_dict, do_update_client=False):
        ancestor_trace_names = np.asarray(ancestor_trace_names)
        traces = data_dict['traces']
        toggled_trace_names = []
        for derived_trace_name in traces:
            trace = traces[derived_trace_name]
            has_selected_ancestors = np.any(np.in1d(ancestor_trace_names, np.asarray(trace.get('ancestors'))))
            if has_selected_ancestors:
                if trace["spectrum_type"] == derived_trace_type:

                    # consider only the first derived trace of a particular type
                    if trace.get("inner_type_rank") == 1:
                        # self.write_info("Toggle " + derived_trace_name + " from is_visible=" + str(data_dict['traces'][derived_trace_name]["is_visible"]))
                        trace["is_visible"] = False if trace["is_visible"] == True else True
                        # self.write_info("Toggle " + derived_trace_name + " intermediate to is_visible=" + str(trace["is_visible"]))
                        traces[derived_trace_name] = trace
                        toggled_trace_names.append(derived_trace_name)
                        # self.write_info("Toggle " + derived_trace_name + " to is_visible=" + str(data_dict['traces'][derived_trace_name]["is_visible"]))
        data_dict["traces"] = traces
        self._set_trace_updates_info(data_dict, updated_trace_names=toggled_trace_names)

        if do_update_client:
            self._update_client()

    def _include_derived_traces(self, spectrum_types, ancestor_trace_names, data_dict, do_update_client=False):
        ancestor_trace_names = np.asarray(ancestor_trace_names)
        for derived_trace_name in data_dict['traces']:
            trace = data_dict['traces'][derived_trace_name]
            has_selected_ancestors = np.any(np.in1d(ancestor_trace_names, np.asarray(trace.get('ancestors'))))
            if has_selected_ancestors:
                if trace["spectrum_type"] in spectrum_types:
                    trace["is_visible"] = True
                else:
                    trace["is_visible"] = False
                data_dict[derived_trace_name] = trace
        if do_update_client:
            self._update_client()

    def _write_info(self, info, file_endding=''):
        if do_log:
            if file_endding != '':
                file_endding = '_' + file_endding
            with open(base_logs_directory + 'info' + file_endding + '.txt', 'a+') as f:
                f.write(str(datetime.now()) + " " + info + "\n")

    def __set_app_data_timestamp(self, timestamp=None):
        if timestamp is not None:
            self.app_data_timestamp['timestamp'] = timestamp  # in sceconds
        else:
            self.app_data_timestamp['timestamp'] = datetime.timestamp(datetime.now())  # in sceconds
        self._write_info("Updated timestamp to " + str(self.app_data_timestamp['timestamp']))

    def _update_client(self, component_names=[], timestamp=None):
        # self.__set_app_data_timestamp(timestamp)
        # https://stackoverflow.com/questions/28947581/how-to-convert-a-dictproxy-object-into-json-serializable-dict
        # self._send_websocket_message(json.dumps(self.app_data.copy()))
        message = {'component_names': component_names, 'timestamp': timestamp}
        self._send_websocket_message(json.dumps(message))

    def _send_websocket_message(self, message):
        self.socketio.emit("update", message)

    def get_data_dict(self, data):
        # return json.loads(data) if data is not None else self.build_app_data()
        return data if data is not None else self._build_app_data()

    def _unsmooth_trace(self, trace_names, application_data, do_update_client=True):
        for trace_name in trace_names:
            traces = application_data['traces']
            trace = traces[trace_name]

            # use original flux stored as flambda
            flux = fl.convert_flux(flux=trace['flambda'], wavelength=trace['wavelength'],
                                   from_flux_unit=FluxUnit.F_lambda, to_flux_unit=trace.get('flux_unit'),
                                   to_wavelength_unit=trace.get('wavelength_unit'))
            trace['flux'] = flux
            traces[trace_name] = trace
            application_data['traces'] = traces

        self._set_trace_updates_info(application_data, updated_trace_names=[n for n in trace_names])

        if do_update_client:
            self._update_client()

    def _get_smoother(self, smoothing_kernel, kernel_width):
        if smoothing_kernel in default_smoothing_kernels:
            smoother = Smoother()
            smoother.set_smoothing_kernel(kernel=smoothing_kernel, kernel_width=int(kernel_width))
        else:  # use smoother defined by user:
            smoother = self.smoother
        return smoother

    def _smooth_trace(self, trace_names, application_data, smoother, do_update_client=True, do_subtract=False,
                      as_new_trace=False, new_trace_name=None):
        added_trace_names = []
        for trace_name in trace_names:
            if trace_name in application_data['traces']:
                traces = application_data['traces']
                trace = traces[trace_name]

                flux = fl.convert_flux(flux=trace['flambda'], wavelength=trace['wavelength'],
                                       from_flux_unit=FluxUnit.F_lambda, to_flux_unit=trace.get('flux_unit'),
                                       to_wavelength_unit=trace.get('wavelength_unit'))

                smoothed_flux = smoother.get_smoothed_flux(flux)

                if do_subtract:
                    smoothed_flux = flux - smoothed_flux

                if not as_new_trace:
                    trace['flux'] = smoothed_flux
                    traces[trace_name] = trace
                else:

                    if new_trace_name is None:
                        names = [name for name in application_data['traces'] if
                                 trace_name in application_data['traces'][name][
                                     "ancestors"] and SpectrumType.SMOOTHED in application_data['traces'][name][
                                     "spectrum_type"]]
                        smoothed_trace_name = "smoothed_" + str(len(names) + 1) + "_" + trace_name
                    else:
                        smoothed_trace_name = new_trace_name

                    ancestors = trace['ancestors'] + [trace_name]

                    f_labmda = fl.convert_flux(flux=[y for y in smoothed_flux],
                                               wavelength=[x for x in trace["wavelength"]],
                                               from_flux_unit=trace['flux_unit'], to_flux_unit=FluxUnit.F_lambda,
                                               to_wavelength_unit=WavelengthUnit.ANGSTROM)

                    smoothed_trace = Trace(name=smoothed_trace_name, wavelength=[x for x in trace["wavelength"]],
                                           flux=[y for y in smoothed_flux], flux_error=trace.get('flux_error'),
                                           ancestors=ancestors, spectrum_type=SpectrumType.SMOOTHED, color="black",
                                           linewidth=1, alpha=1.0, wavelength_unit=trace['wavelength_unit'],
                                           flux_unit=trace['flux_unit'], flambda=f_labmda,
                                           flambda_error=trace.get("flambda_error"), catalog=trace['catalog']).to_dict()

                    self._set_color_for_new_trace(smoothed_trace, application_data)
                    traces[smoothed_trace_name] = smoothed_trace
                    added_trace_names.append(smoothed_trace_name)

                application_data['traces'] = traces

                # if kernel is custom, add it to the data dict:
                current_smoothing_kernels = application_data['smoothing_kernel_types']
                self._write_info("current_smoothing_kernels1: " + str(current_smoothing_kernels))
                if smoother.kernel_func_type not in current_smoothing_kernels:
                    current_smoothing_kernels.append(smoother.kernel_func_type)
                # self.write_info("current_smoothing_kernels2: " + str(current_smoothing_kernels))
                application_data['smoothing_kernel_types'] = current_smoothing_kernels
                # self.write_info("application_data['smoothing_kernel_types']: " + str(application_data['smoothing_kernel_types']))

        if as_new_trace:
            self._set_trace_updates_info(application_data, added_trace_names=added_trace_names)
        else:
            self._set_trace_updates_info(application_data, updated_trace_names=[n for n in trace_names if
                                                                                n in application_data['traces']])
        if do_update_client:
            self._update_client()

    def _rescale_axis(self, application_data, to_wavelength_unit=WavelengthUnit.ANGSTROM,
                      to_flux_unit=FluxUnit.F_lambda, do_update_client=False):
        traces = application_data['traces']
        for trace_name in traces:
            rescaled_trace = self._get_rescaled_axis_in_trace(traces[trace_name], to_wavelength_unit=to_wavelength_unit,
                                                              to_flux_unit=to_flux_unit)
            traces[trace_name] = rescaled_trace

        application_data['traces'] = traces

        self._set_axis_units(application_data, to_wavelength_unit, to_flux_unit)

        self._set_trace_updates_info(application_data, updated_trace_names=[name for name in traces])

        if do_update_client:
            self._update_client()

    def _get_rescaled_axis_in_trace(self, trace, to_wavelength_unit=WavelengthUnit.ANGSTROM,
                                    to_flux_unit=FluxUnit.F_lambda):

        # Documentation:
        # https://synphot.readthedocs.io/en/latest/synphot/units.html
        # https://synphot.readthedocs.io/en/latest/api/synphot.units.convert_flux.html#synphot.units.convert_flux

        # for wavelength axis:
        trace['wavelength'] = fl.convert_wavelength(wavelength=trace['wavelength'],
                                                    from_wavelength_unit=trace['wavelength_unit'],
                                                    to_wavelength_unit=to_wavelength_unit)
        trace['wavelength_unit'] = to_wavelength_unit

        # for flux axis:
        if trace.get('flux_unit') == FluxUnit.AB_magnitude and to_flux_unit != FluxUnit.AB_magnitude:
            if trace.get("flambda") is not None and len(trace.get("flambda")) > 0:
                trace['flux'] = fl.convert_flux(flux=trace.get("flambda"), wavelength=trace['wavelength'],
                                                from_flux_unit=FluxUnit.F_lambda, to_flux_unit=to_flux_unit,
                                                to_wavelength_unit=to_wavelength_unit)
                trace['flux_error'] = fl.convert_flux(flux=trace.get("flambda_error"), wavelength=trace['wavelength'],
                                                      from_flux_unit=FluxUnit.F_lambda, to_flux_unit=to_flux_unit,
                                                      to_wavelength_unit=to_wavelength_unit)
            else:
                trace['flux'] = fl.convert_flux(flux=trace['flux'], wavelength=trace['wavelength'],
                                                from_flux_unit=trace.get('flux_unit'), to_flux_unit=to_flux_unit,
                                                to_wavelength_unit=to_wavelength_unit)
                trace['flux_error'] = fl.convert_flux(flux=trace['flux_error'], wavelength=trace['wavelength'],
                                                      from_flux_unit=trace.get('flux_unit'), to_flux_unit=to_flux_unit,
                                                      to_wavelength_unit=to_wavelength_unit)
        else:
            trace['flux'] = fl.convert_flux(flux=trace['flux'], wavelength=trace['wavelength'],
                                            from_flux_unit=trace.get('flux_unit'), to_flux_unit=to_flux_unit,
                                            to_wavelength_unit=to_wavelength_unit)
            trace['flux_error'] = fl.convert_flux(flux=trace['flux_error'], wavelength=trace['wavelength'],
                                                  from_flux_unit=trace.get('flux_unit'), to_flux_unit=to_flux_unit,
                                                  to_wavelength_unit=to_wavelength_unit)

        trace['flux_unit'] = to_flux_unit
        return trace

    def _bin_wavelength_axis(self, trace_names, application_data, bin_size, wavelength_unit, flux_unit,
                             do_update_client=False):
        # convert to
        if bin_size <= 0:
            raise Exception("bin_size should be grater than 0.")

        added_traces = []
        for trace_name in trace_names:

            trace = application_data['traces'][trace_name].copy()

            wave_binned = []
            flux_binned = []
            flux_err_binned = []
            n = len(trace['flux'])

            for i in range(0, n, bin_size):
                if i < n - bin_size + 1:
                    wave_binned.append(np.mean(trace['wavelength'][i:i + bin_size]))
                    flux_binned.append(np.mean(trace['flux'][i:i + bin_size]))
                    if len(trace['flux_error']) > 0:
                        flux_err_binned.append(np.mean(trace['flux_error'][i:i + bin_size]))

            flambda = fl.convert_flux(flux=flux_binned, wavelength=wave_binned, from_flux_unit=flux_unit,
                                      to_flux_unit=FluxUnit.F_lambda, to_wavelength_unit=WavelengthUnit.ANGSTROM)
            flambda_err = fl.convert_flux(flux=flux_err_binned, wavelength=wave_binned, from_flux_unit=flux_unit,
                                          to_flux_unit=FluxUnit.F_lambda, to_wavelength_unit=WavelengthUnit.ANGSTROM)
            trace['wavelength'] = wave_binned
            trace['flux'] = flux_binned
            trace['flux_error'] = flux_err_binned
            trace['flambda'] = [x for x in flambda]
            trace['flambda_err'] = [x for x in flambda_err]
            trace['ancestors'] = trace['ancestors'] + [trace_name]
            for i in range(100):  # revise
                name = "binned_" + str(i) + "_" + trace['name']
                if name not in application_data['traces']:
                    trace['name'] = name
                    break
            if trace['name'] == trace_name:
                trace['name'] = "binned_" + str(uuid.uuid1()) + "_" + trace_name

            added_traces.append(trace)

        self._set_colors_for_new_traces(added_traces, self._get_current_colors(application_data))
        self._add_trace_to_data(application_data, added_traces)

        if do_update_client:
            self._update_client()

    def _get_model_fitter(self, trace_name, application_data, fitting_model, selected_data):

        # trace = application_data['traces'].get(trace_name)

        curve_number = self._get_curve_mapping(application_data)[trace_name]

        x = np.asarray([point['x'] for point in selected_data["points"] if point['curveNumber'] == curve_number])
        y = np.asarray([point['y'] for point in selected_data["points"] if point['curveNumber'] == curve_number])

        if fitting_model in default_fitting_models:

            model, fitter = ModelFitter.get_model_with_fitter(fitting_model, x, y)
            model_type = fitting_model

        else:
            fitter = self.model_fitter.fitter
            model = self.model_fitter.model
            model_type = FittingModels.CUSTOM

        return ModelFitter(model, fitter, model_type)

    def _fit_model_to_flux(self, trace_names, application_data, model_fitters, selected_data, median_filter_width=1,
                           do_update_client=False, add_fit_subtracted_trace=False):

        # Documentation:
        # http://learn.astropy.org/rst-tutorials/User-Defined-Model.html
        # https://docs.astropy.org/en/stable/modeling/new-model.html
        # https://docs.astropy.org/en/stable/modeling/index.html
        # https://docs.astropy.org/en/stable/modeling/reference_api.html

        # added_trace_names = []
        fitted_info_list = []
        fitted_traces = []
        for model_fitter in model_fitters:
            for trace_name in trace_names:

                trace = application_data['traces'].get(trace_name)
                curve_number = self._get_curve_mapping(application_data)[trace_name]

                x = np.asarray(
                    [point['x'] for point in selected_data["points"] if point['curveNumber'] == curve_number])
                y = np.asarray(
                    [point['y'] for point in selected_data["points"] if point['curveNumber'] == curve_number])
                ind = [point['pointIndex'] for point in selected_data["points"] if point['curveNumber'] == curve_number]
                y_err = np.asarray(trace["flux_error"])[ind] if trace["flux_error"] is not None or \
                                                                len(trace["flux_error"]) > 0 else None

                if median_filter_width is not None and median_filter_width >= 1:
                    pass

                min_x, max_x = np.min(x), np.max(x)
                wavelength = np.array(trace["wavelength"])
                ind2 = (wavelength >= min_x) & (wavelength <= max_x)
                wave = wavelength[ind2]

                fitter = model_fitter.fitter
                model = model_fitter.model
                fitting_model_type = model_fitter.model_type

                self._write_info("x :" + str(x))
                self._write_info("y :" + str(y))
                self._write_info("err :" + str(y_err))
                fitted_model = fitter(model, x, y, weights=1. / y_err)

                x_grid = np.linspace(min_x, max_x, 5 * len(x))
                x_grid = wave
                y_grid = fitted_model(x_grid)

                parameter_errors = np.sqrt(np.diag(fitter.fit_info.get('param_cov'))) if fitter.fit_info.get(
                    'param_cov') is not None else [None for x in fitted_model.parameters]
                parameters_covariance_matrix = fitter.fit_info.get('param_cov')

                fitted_trace_name = "fit" + str(len(application_data['fitted_models']) + 1) + "_" + trace_name
                ancestors = trace['ancestors'] + [trace_name]
                flambda = [f for f in np.asarray(trace['flambda'])[ind]]
                fitted_trace = Trace(name=fitted_trace_name, wavelength=[x for x in x_grid], flux=[y for y in y_grid],
                                     ancestors=ancestors, spectrum_type=SpectrumType.FIT, color="black", linewidth=1,
                                     alpha=1.0, wavelength_unit=trace['wavelength_unit'], flux_unit=trace['flux_unit'],
                                     flambda=flambda, catalog=trace['catalog']).to_dict()

                fitted_traces.append(fitted_trace)

                if add_fit_subtracted_trace:
                    fitted_trace_name = "fitsub_" + str(len(application_data['fitted_models']) + 1) + "_" + trace_name
                    ancestors = trace['ancestors'] + [trace_name]

                    # flux = np.array(trace.get('flux'))
                    flux = np.array(trace["flux"])[ind2]
                    flux = flux - fitted_model(wave)
                    # flux[ind] = diff

                    f_labmda = fl.convert_flux(flux=flux, wavelength=wave,
                                               from_flux_unit=trace['flux_unit'], to_flux_unit=FluxUnit.F_lambda,
                                               to_wavelength_unit=WavelengthUnit.ANGSTROM)

                    fitted_trace = Trace(name=fitted_trace_name, wavelength=[x for x in wave],
                                         flux=[y for y in flux],
                                         ancestors=ancestors, spectrum_type=SpectrumType.FIT, color="black",
                                         linewidth=1, alpha=1.0,
                                         wavelength_unit=trace['wavelength_unit'], flux_unit=trace['flux_unit'],
                                         flambda=f_labmda, catalog=trace['catalog']).to_dict()

                    fitted_traces.append(fitted_trace)

                # equivalent width

                fitted_info = {}
                fitted_info['trace_name'] = fitted_trace_name
                fitted_info['original_trace'] = trace_name
                fitted_info['ancestors'] = ancestors + [fitted_trace_name]
                fitted_info['model'] = fitting_model_type
                fitted_info['parameter_names'] = [x for x in fitted_model.param_names]
                fitted_info['parameter_values'] = {x: y for (x, y) in
                                                   zip(fitted_model.param_names, fitted_model.parameters)}
                fitted_info['covariance'] = parameters_covariance_matrix
                fitted_info['parameter_errors'] = {x: y for (x, y) in zip(fitted_model.param_names, parameter_errors)}
                fitted_info['selection_indexes'] = ind
                fitted_info['wavelength_unit'] = trace['wavelength_unit']
                fitted_info['flux_unit'] = trace['flux_unit']
                fitted_info_list.append(fitted_info)

                current_fitting_model_types = application_data['fitting_model_types']
                if fitting_model_type not in current_fitting_model_types:
                    current_fitting_model_types.append(fitting_model_type)
                    application_data['fitting_model_types'] = current_fitting_model_types

                fitted_info_list.append(fitted_info)

        self._set_colors_for_new_traces(fitted_traces, self._get_current_colors(application_data))
        self._add_trace_to_data(application_data, fitted_traces, do_update_client=False)

        fitted_models = application_data['fitted_models']
        for fitted_model_info in fitted_info_list:
            fitted_models[fitted_model_info.get('trace_name')] = fitted_model_info
        application_data['fitted_models'] = fitted_models

        if do_update_client:
            self._update_client()

        return fitted_info_list

    def _get_selection(self, selected_data, data_dict):
        selection = {}
        if selected_data != {} and selected_data is not None:
            selection = {key: value for key, value in selected_data.items()}
            # adding trace name to each points:
            curve_mapping_reversed = {ind: name for (name, ind) in self._get_curve_mapping(data_dict).items()}
            points = []
            for point in selection['points']:
                point['trace_name'] = curve_mapping_reversed[point['curveNumber']]
                points.append(point)
            selection['points'] = points
            return selection

        return selection

    def _set_selection(self, trace_name, application_data, selection_indices=[], do_update_client=False):
        # curve_mapping = {name: ind for ind, name in enumerate(application_data['traces'])}
        curve_number = self._get_curve_mapping(application_data)[trace_name]

        selection = application_data["selection"]
        new_points = [point for point in selection["points"] if point['curveNumber'] != curve_number]

        trace_points = []
        for ind in selection_indices:
            point = {}
            point['curveNumber'] = curve_number
            point['pointNumber'] = ind
            point['pointIndex'] = ind
            point['trace_name'] = trace_name
            point['x'] = application_data['traces'][trace_name]["wavelength"][ind]
            point['y'] = application_data['traces'][trace_name]["flux"][ind]
            trace_points.append(point)

        new_points = new_points + trace_points
        selection['points'] = new_points
        application_data["selection"] = selection

        if do_update_client:
            self._update_client()

    def _update_trace_properties(self, data_dict, properties_list, do_update_client=True, also_remove_children=False):

        trace_list = [data_dict['traces'][trace] for trace in data_dict['traces']]
        for properties in properties_list:
            rank = int(properties['rank'])
            trace = trace_list[rank]
            old_trace_name = trace['name']
            new_trace_name = properties['name']
            for property in properties:
                if property in trace and property != 'ancestors':
                    trace[property] = properties[property]
            trace_list[rank] = trace

            if new_trace_name is not None and new_trace_name != old_trace_name:
                # change name in ancestors of other traces:

                trace_list2 = []
                for i, trace2 in enumerate(trace_list):
                    ancestors = trace2['ancestors']
                    if old_trace_name in ancestors:
                        ancestors = [new_trace_name if ancestor == old_trace_name else ancestor for ancestor in
                                     ancestors]
                    trace2['ancestors'] = ancestors
                    trace_list2.append(trace2)

                trace_list = [t for t in trace_list2]

        data_dict['traces'] = {trace['name']: trace for trace in trace_list}

        traces_in_properties = [prop['name'] for prop in properties_list]
        traces_to_delete = [trace_name for trace_name in data_dict['traces'] if trace_name not in traces_in_properties]
        self._remove_traces(traces_to_delete, data_dict, do_update_client=False,
                            also_remove_children=also_remove_children)
        self._set_trace_updates_info(data_dict, removed_trace_names=traces_to_delete,
                                     updated_trace_names=traces_in_properties)

        if do_update_client:
            self._update_client()

    def _get_line_analysis(self, trace_names, application_data, selected_data, continuum_trace, median_window=10,
                           as_new_trace=False, do_update_client=False):

        # Documentation:
        # http://learn.astropy.org/rst-tutorials/User-Defined-Model.html
        # https://docs.astropy.org/en/stable/modeling/new-model.html
        # https://docs.astropy.org/en/stable/modeling/index.html
        # https://docs.astropy.org/en/stable/modeling/reference_api.html

        line_analysis_dict = {}

        continuum = application_data['traces'][continuum_trace]
        continuum_x = np.asarray(continuum['wavelength'])
        continuum_y = np.asarray(continuum['flux'])

        added_traces = []
        for trace_name in trace_names:

            trace = application_data['traces'].get(trace_name)
            curve_number = self._get_curve_mapping(application_data)[trace_name]

            x = np.asarray([point['x'] for point in selected_data["points"] if point['curveNumber'] == curve_number])
            y = np.asarray([point['y'] for point in selected_data["points"] if point['curveNumber'] == curve_number])
            ind = [point['pointIndex'] for point in selected_data["points"] if point['curveNumber'] == curve_number]
            y_err = np.asarray(trace["flux_error"])[ind] if trace["flux_error"] is not None or len(
                trace["flux_error"]) > 0 else None
            spectrum = Spectrum1D(spectral_axis=x * WavelengthUnit.get_astropy_unit(trace["wavelength_unit"]),
                                  flux=y * FluxUnit.get_astropy_unit(trace["flux_unit"]))

            ind2 = []
            for _x in x:
                i = np.where(continuum_x == _x)
                if len(i[0]) > 0:
                    ind2.append(i[0][0])

            continuum_spec = Spectrum1D(
                spectral_axis=continuum_x[ind2] * WavelengthUnit.get_astropy_unit(continuum["wavelength_unit"]),
                flux=continuum_y[ind2] * FluxUnit.get_astropy_unit(continuum["flux_unit"]))
            norm_spectrum = spectrum / continuum_spec
            diff_spectrum = spectrum - continuum_spec

            specline = SpectralLine()
            specline.line = "user-defined"
            specline.wavelength = analysis.centroid(spectrum=norm_spectrum, region=None).value
            specline.ew = analysis.equivalent_width(spectrum=norm_spectrum, regions=None).value
            specline.area = analysis.line_flux(diff_spectrum, regions=None).value
            specline.sigma = analysis.gaussian_sigma_width(diff_spectrum).value
            specline.cont_level = np.mean(continuum_spec.flux).value
            specline.wavelength_unit = trace['wavelength_unit']
            specline.flux_unit = trace['flux_unit']

            line_trace = Trace()
            line_trace_name = "Line_" + trace_name
            line_trace.name = line_trace_name
            line_trace.catalog = trace['catalog']
            line_trace.wavelength = [i for i in x]
            line_trace.flux = [i for i in y]
            line_trace.flux_error = [i for i in y_err]
            line_trace.wavelength_unit = trace['wavelength_unit']
            line_trace.flux_unit = trace['flux_unit']
            line_trace.spectrum_type = SpectrumType.LINE
            line_trace.spectral_lines = [specline.to_dict()]
            line_trace.ancestors = trace['ancestors'] + [trace_name]
            line_trace.flambda = [x for x in np.array(trace['flambda'])[ind]]
            line_trace.flambda_error = [x for x in np.array(trace['flambda_error'])[ind]]
            line_trace.linewidth = 1
            line_trace.color = "black"
            line_trace = line_trace.to_dict()
            added_traces.append(line_trace)
            # added_trace_names.append(line_trace_name)

        self._set_colors_for_new_traces(added_traces, self._get_current_colors(application_data))
        self._add_trace_to_data(application_data, added_traces, do_update_client=False)

        if do_update_client:
            self._update_client()

    def _get_curve_mappingOLD(self, application_data):
        curve_mapping = {}
        for index, trace_name in enumerate(application_data['traces']):
            if application_data['traces'][trace_name]['is_visible']:
                curve_mapping[trace_name] = index

        return curve_mapping

    def _get_curve_mapping(self, application_data):
        curve_mapping = {}
        index = 0
        for trace_name in application_data['traces']:
            if application_data['traces'][trace_name]['is_visible']:
                curve_mapping[trace_name] = index
                index += 1

        return curve_mapping

    ######################################################################################################################
    ########  Trace manipulation/analysis functions for execution within Jupyter  ##################################################################

    def set_smoothing_kernel(self, kernel=SmoothingKernels.GAUSSIAN1D, kernel_width=20, custom_array_kernel=None,
                             custom_kernel_function=None, function_array_size=21):
        """
        Sets the smoothing kernel from several kernel options: predefined kernels listed  in the SmoothingKernels class,
        custom list of integers defining a discrete kernel, or custom kernel function of class astropy.modeling.Fittable1DModel.
        :param kernel: String defining kernel from SmoothingKernels class.
        :param kernel_width: integer defining kernel width
        :param custom_array_kernel: array or list of integers defining the custom kernel
        :param custom_kernel_function: function of class astropy.modeling.Fittable1DModel
        :param function_array_size: integer defining kernel width for custom kernel function.
        """
        self.smoother.set_smoothing_kernel(kernel, kernel_width, custom_array_kernel, custom_kernel_function,
                                           function_array_size)
        if self.smoother.kernel_func_type not in self.app_data["smoothing_kernel_types"]:
            smoothing_kernel_types = self.app_data.get("smoothing_kernel_types")
            smoothing_kernel_types.append(self.smoother.kernel_func_type)
            self.app_data["smoothing_kernel_types"] = smoothing_kernel_types
            self._update_client()

    def smooth_trace(self, trace_name, do_subtract=False):
        """
        Smooths a  trace after the kernel is set with 'set_smoothing_kernel'
        :param trace_name: name of trace
        :param do_subtract: True if the smoothed trace is subtracted from the original trace. False otherwise.
        """
        self._initialize_updates(self.app_data)
        self._smooth_trace([trace_name], self.app_data, self.smoother, do_update_client=True, do_subtract=do_subtract)

    def reset_smoothing(self, trace_name):
        """
        Resets the smoothing previously done on a trace
        :param trace_name: name of trace
        """
        self._initialize_updates(self.app_data)
        self._unsmooth_trace([trace_name], self.app_data, do_update_client=True)

    def set_custom_model_fitter(self, model, fitter):
        """
        Sets the instances of a model and fitter in order to perform model fitting on a trace.
        :param model: model instance from astropy.modeling,models
        :param fitter: fitter instance from astropy.modeling,fitting
        """
        self.model_fitter = ModelFitter(model, fitter, FittingModels.CUSTOM)
        if self.model_fitter.model_type not in self.app_data["fitting_model_types"]:
            fitting_model_types = self.app_data.get("fitting_model_types")
            fitting_model_types.append(self.model_fitter.model_type)
            self.app_data["fitting_model_types"] = fitting_model_types
            self._update_client()

    def set_model_fitter(self, trace_name, fitting_model=FittingModels.GAUSSIAN_PLUS_LINEAR):
        """
        Sets the instances of a model and fitter in order to perform model fitting on a trace.
        :param trace_name: name of trace
        :param fitting_model: model defined by the members of class FittingModels
        """
        self.model_fitter = self._get_model_fitter(trace_name, self.app_data, fitting_model, self.app_data['selection'])

    def fit_model(self, trace_name, median_filter_width=1, add_fit_subtracted_trace=False):
        """
        Fits select flux data points with model.
        :param trace_name:
        :param median_filter_width: width of median filter applied to data points before fitting. This Functionality not there yet.
        :param add_fit_subtracted_trace: Boolean, defining whether to add the fit-subtracted data points as an
        additional trace.
        """
        self._initialize_updates(self.app_data)
        fitting_info_list = self._fit_model_to_flux([trace_name], self.app_data, [self.model_fitter],
                                                    self.app_data['selection'], median_filter_width=median_filter_width,
                                                    do_update_client=True,
                                                    add_fit_subtracted_trace=add_fit_subtracted_trace)
        return fitting_info_list[0]

    def get_data_selection(self):
        """
        Returns array of data points that were selected with the graphical interface,
        """
        return self.app_data.get("selection")

    def set_data_selection(self, trace_name, selection_indices=[]):
        """
        Sets the instance object with particular data points being selected.
        :param trace_name: name (string) of trace whose data points are being selected.
        :param selection_indices: list of integers defining the indexes of th epoints being selected.
        """
        self._set_selection(trace_name, self.app_data, selection_indices, do_update_client=True)

    def add_spectrum(self, spectrum, is_visible=True):
        """
        Adds a spectrum to the viewer.
        ----------
        spectrum: `specdash.models.data_models.Spectrum` or `list(specdash.models.data_models.Spectrum)`
            Spectrum object of type specdash.models.data_models.Spectrum, or list containing those type of objects.
        is_visible: `bool`
            `True` if the spectrum is to be shown in the plot, `False` otherwise.

        Returns
        -------

        """
        self._initialize_updates(self.app_data)
        _spectrum = spectrum if type(spectrum) == list else [spectrum]
        _is_visible = is_visible if type(is_visible) == list else [is_visible]
        if len(_spectrum) != len(_is_visible):
            raise Exception("spectrum and is_visible parameters should have the same length")

        _s = Spectrum()
        for i, spectrum in enumerate(_spectrum):
            if type(spectrum) != type(_s):
                raise Exception("Invalid type of input spectrum parameter")
            if type(_is_visible[i]) != bool:
                raise Exception("Invalid type of input is_visible parameter")

        added_traces = []
        for i, spectrum in enumerate(_spectrum):
            trace = Trace()
            trace.from_spectrum(spectrum, is_visible=_is_visible[i])
            trace = trace.to_dict()

            wavelength_unit = self.app_data['axis_units'].get('wavelength_unit')
            flux_unit = self.app_data['axis_units'].get('flux_unit')
            if wavelength_unit is not None and flux_unit is not None:
                trace = self._get_rescaled_axis_in_trace(trace, to_wavelength_unit=wavelength_unit,
                                                         to_flux_unit=flux_unit)
            else:
                self._set_axis_units(self.app_data, wavelength_unit, flux_unit)
            added_traces.append(trace)

        self._add_trace_to_data(self.app_data, added_traces, do_update_client=False)

        # self._set_trace_updates_info(self.app_data, added_trace_names=[s.name for s in _spectrum])
        self._update_client()

    def get_spectrum(self, name):
        """

        Parameters
        ----------
        name

        Returns
        -------

        """
        t = self.app_data['traces'][name]
        s = Spectrum(name=name, wavelength=t['wavelength'], flux=t['flux'], flux_error=t['flux_error'],
                     masks=t['masks'],
                     mask_bits=t['mask_bits'], wavelength_unit=t['wavelength_unit'], flux_unit=t['flux_unit'],
                     catalog=t['catalog'], spectrum_type=t['spectrum_type'], color=t['color'], linewidth=t['linewidth'],
                     alpha=t['alpha'])
        return s

    def get_trace_names(self):
        """

        Returns
        -------

        """
        return [name for name in self.app_data['traces']]

    def add_spectrum_from_file(self, file_path, catalog_name, display_name=None, to_wavelength_unit=None,
                               to_flux_unit=None):
        """

        Parameters
        ----------
        file_path
        catalog_name
        display_name
        to_wavelength_unit
        to_flux_unit

        Returns
        -------

        """
        if type(file_path) == str and (type(display_name) == str or display_name is None):
            file_path = [file_path]
            display_name = [display_name]
        else:
            if type(file_path) == list and display_name is None:
                trace_name = [None for i in file_path]
            if type(file_path) != list or (type(display_name) != list and display_name is not None):
                raise Exception("Wrong type for file_path or trace_name parameters.")

        if len(file_path) != len(display_name):
            raise Exception("file_path and name should be lists of the same length")

        for i in range(len(file_path)):
            self._add_spectrum_from_file(file_path[i], self.app_data, to_wavelength_unit, to_flux_unit, catalog_name,
                                         display_name[i], do_update_client=False)

        self._update_client()

    def add_spectrum_from_id(self, specid, catalog_name, display_name=None, to_wavelength_unit=None, to_flux_unit=None):
        """

        Parameters
        ----------
        specid
        catalog_name
        display_name
        to_wavelength_unit
        to_flux_unit

        Returns
        -------

        """

        # self._initialize_updates(self.app_data)

        if type(specid) == str and (type(display_name) == str or display_name is None):
            specid = [specid]
            display_name = [display_name]
        else:
            if type(specid) == list and display_name is None:
                name = [None for i in specid]
            if type(specid) != list or (type(display_name) != list and display_name is not None):
                raise Exception("Wrong type for specid or name parameters.")

        if len(specid) != len(display_name):
            raise Exception("specid and name should be lists of the same length")

        self._load_from_specid(specid, display_name, to_wavelength_unit, to_flux_unit, self.app_data, catalog_name,
                               do_update_client=False)

        self._update_client()

    def get_catalog_names(self):
        """

        Returns
        -------

        """
        return input.get_supported_catalogs()

    def update_trace(self, name, trace):
        """

        Parameters
        ----------
        name
        trace

        Returns
        -------

        """
        self.app_data['traces'][name] = trace
        self._update_client()

    def remove_trace(self, name, also_remove_children=True):
        """

        Parameters
        ----------
        name
        also_remove_children

        Returns
        -------

        """
        self._remove_traces([name], self.app_data, do_update_client=True, also_remove_children=also_remove_children)

    def toggle(self, name=None, is_visible=True, all_traces=True):
        """

        Parameters
        ----------
        name
        is_visible
        all_traces

        Returns
        -------

        """

        if type(name) == str:
            name = [name]

        if name is None and all_traces is True:
            name = self.get_trace_names()

        traces = self.app_data['traces']
        for _name in name:
            if _name not in traces:
                raise Exception(_name + " not found in trace list")

            trace = traces[_name]
            trace["is_visible"] = True if is_visible is True else False
            traces[_name] = trace

        self.app_data['traces'] = traces
        self._update_client()

    def set_axis_units(self, wavelength_unit=WavelengthUnit.ANGSTROM, flux_unit=FluxUnit.F_lambda):
        """

        Parameters
        ----------
        wavelength_unit
        flux_unit

        Returns
        -------

        """
        self._rescale_axis(self.app_data, to_wavelength_unit=wavelength_unit, to_flux_unit=flux_unit)
        self._update_client()
