import json
import dash
from specdash import base_logs_directory, example_specids, do_log, max_num_traces
from .models.enum_models import FluxUnit, SpectrumType
from datetime import datetime
from dash import no_update
from dash.dependencies import Output, Input, State, ClientsideFunction
import traceback
from specdash.smoothing.smoother import Smoother, SmoothingKernels, default_smoothing_kernels
from urllib.parse import urlparse, parse_qsl
import base64
from flask import request, session, g
from specdash.logging.logger import log_message, LoggedMetadata
from collections import OrderedDict

def load_callbacks(self): # self is passed as the Viewer class

    try:

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='toggle_main_page'
            ),
            [Output('main-page', 'style'),Output('docs-page', 'style')],
            [Input('url', 'pathname')],
        )

        @self.app.callback(
            Output("download-file", "data"),
            [Input("download-button", "n_clicks")],
            [State('store', 'data'),State('session-id', 'children')], prevent_initial_callbacks=True
        )
        def func(n_clicks, data_dict, session_id):
            task_name = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
            logged_metadata = LoggedMetadata()
            logged_metadata['session_id'] = session_id
            logged_metadata['task_name'] = task_name
            try:
                if n_clicks is not None and data_dict is not None:
                    data_dict['updates']['added_traces'] = [name for name in data_dict['traces']]
                    data_dict['updates']['added_zdists'] = [name for name in data_dict['redshift_distributions']]
                    return dict(content=json.dumps(data_dict), filename="specdash-data.json")
                else:
                    return no_update
            except Exception as e:
                exs = str(e)
                logged_metadata.exception = e
                return no_update, no_update, {'header': "Error", "body": exs}
            finally:
                try:
                    log_message(request=request, logged_metadata=logged_metadata, do_log=do_log)
                except Exception as ex:
                    pass

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_lines_redshift'
            ),
            [Output("redshift-slider", "value"),Output("redshift_input","value"),Output("redshift-dropdown", "value")],
            [Input("redshift-slider", "value"),Input("redshift_input","value"),Input("redshift-dropdown", "value")],
        )

        # update main spec figure every time the data changes
        # @self.app.callback(
        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_figure'
            ),
            [Output('spec-graph', 'figure'),Output('graph_trace_info', 'data')],
            [
             Input('store', 'modified_timestamp'), Input('spectral-lines-switch', 'on'),Input('sky-lines-switch', 'on'),Input('artificial-lines-switch', 'on'),
             Input('redshift-slider', 'value'),Input('spectral_lines_dropdown', 'value'),Input('sky_lines_dropdown', 'value'),Input('artificial_lines_dropdown', 'value'),
             Input('mask_switch', 'on'),
             Input('dropdown-for-masks', 'value'),
             Input('show_error_button', 'n_clicks'),
             Input('store', 'data'),
             Input("dropdown-for-specmodels","value"),
             Input("show_photometry_button","n_clicks"),
             Input("show_barchart_button", "n_clicks"),
            ],
            [#State('store', 'data'),
             State('spectral_lines_dict','value'),
             State('sky_lines_dict', 'value'),
             State('artificial_lines_dict', 'value'),
             State('dropdown-for-traces', 'value'),
             State('graph-settings', 'data')
            ]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_zdist_figure'
            ),
            Output('zdist-graph', 'figure'),
            # [Input('store', 'data')],
            [Input('store', 'modified_timestamp'),
             Input('store', 'data'),
             Input('show_zdistlog_button', 'n_clicks'),
            ],
            [
             State('dropdown-for-traces', 'value'),
            ]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_trace_dropdown_values'
            ),
            Output('dropdown-for-traces', 'value'),
            [Input("select_all_traces_button", "n_clicks"),Input('store', 'data')],
            [State('dropdown-for-traces', 'value')]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_regions_dropdown_options'
            ),
            Output('dropdown_for_regions', 'options'),
            [Input('store', 'data')],
        )



        # update dropdown of traces every time the data changes
        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_dropdown_options'
            ),
            Output('dropdown-for-traces', 'options'),
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
            #[State('store', 'data')]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_redshift_dropdown_options'
            ),
            Output('redshift-dropdown', 'options'),
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_dropdown_options_for_specmodels'
            ),
            Output('dropdown-for-specmodels', 'options'),
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_masks_dropdown'
            ),
            Output('dropdown-for-masks', 'options'),
            [Input('store', 'modified_timestamp'),Input('store', 'data')]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_info_content'
            ),
            Output('info_content', 'children'),
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_current_data_selection_table'
            ),
            [Output("current_data_selection_table", 'data'), Output("current_data_selection_table", 'columns'), Output("current_data_selection_table", 'page_current'), Output("current_data_selection_table", 'tooltip_data')],
            [Input('spec-graph', 'selectedData')],
            [State('store', 'data'),State('wavelength-unit', 'value'),State('flux-unit', 'value')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_traces_table'
            ),
            [Output("traces_table", 'data'), Output("traces_table", 'columns'), Output("traces_table", 'style_data_conditional'), Output('color_picker', 'value')],
            [Input('store', 'data'), Input('color_picker', 'value'),Input("traces_table", 'active_cell'), Input("traces_table", 'data')],
        )

        for table_id in ["traces_table",'current_data_selection_table',"current_data_selection_table2",'fitted_models_table','measured_lines_table']:
            self.app.clientside_callback(
                ClientsideFunction(
                    namespace='clientside',
                    function_name='set_page_size'
                ),
                Output(table_id, 'page_size'),
                Input(table_id+"_page_size_input", 'value'),
            )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_fitted_models_table'
            ),
            #[Output('measured_lines_table', 'data'),Output('measured_lines_table', 'columns'),Output('measured_lines_table', 'tooltip_data')],
            [Output("fitted_models_table", 'data'), Output("fitted_models_table", 'columns'), Output("fitted_models_table", 'tooltip_data')],
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_measured_lines_table'
            ),
            #[Output('measured_lines_table', 'data'),Output('measured_lines_table', 'columns'),Output('measured_lines_table', 'tooltip_data')],
            [Output("measured_lines_table", 'data'), Output("measured_lines_table", 'columns')],
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='set_line_analysis_table'
            ),
            [Output("line_analysis_table", 'data'), Output("line_analysis_table", 'columns')],
            [Input('store', 'modified_timestamp'),Input('store', 'data')],
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='toggle_loading_modal'
            ),
            Output("load-spectra-modal", "is_open"),
            [Input("open-loadingmodal-button", "n_clicks"),
             Input("close-loadingmodal-button", "n_clicks"),
             Input('store', 'data')],
            [State("load-spectra-modal", "is_open")]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='toggle_traces_modal'
            ),
            Output("list-traces-modal", "is_open"),
            [
                Input("open-list-traces-button", "n_clicks"),
                Input("close-tracesmodal-button", "n_clicks"),
                Input("save-trace-changes-button", "n_clicks"),
            ],
            [State("list-traces-modal", "is_open")]
        )

        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='toggle_info_modal'
            ),
            [Output("info-modal", "is_open"),Output("info-modal-header", "children"),Output("info-modal-body", "children")],
            [Input("close-infomodal-button", "n_clicks"),
             Input('info-message', 'modified_timestamp'), Input('info-message', 'data')],
            [State("info-modal", "is_open"),State("info-modal-header", "children"),State("info-modal-body", "children")],
        )

        trace_variable_names = ['trace_' + str(i) for i in range(max_num_traces)]
        zdist_variable_names = ['zdist_' + str(i) for i in range(max_num_traces)]
        self.app.clientside_callback(
            ClientsideFunction(
                namespace='clientside',
                function_name='build_app_data'
            ),
            Output("store", "data"),
            [Input(trace_variable_name, 'data') for trace_variable_name in trace_variable_names] + [Input(zdist_variable_name, 'data') for zdist_variable_name in zdist_variable_names],
            [State("store_intermediate", "data")],
        )

        # for server-side callback:

        #output_list = [Output('store_intermediate', 'data'), Output('graph-settings', 'data'), Output('info-message', 'data'),Output('trace_store_mapping', 'data'),Output('updated_traces', 'data')]
        output_list = [Output('store_intermediate', 'data'), Output('graph-settings', 'data'),Output('info-message', 'data')]
        output_list += [Output(trace_variable_name, 'data') for trace_variable_name in trace_variable_names]
        output_list += [Output(zdist_variable_name, 'data') for zdist_variable_name in zdist_variable_names]

        input_list =  [
                        Input("pull_trigger", "value"),
                        Input("remove_trace_button", "n_clicks"),
                        Input('upload-data', 'contents'),
                        Input('trace_smooth_button', 'n_clicks'),
                        Input('trace_smooth_subtract_button', 'n_clicks'),
                        Input('trace_unsmooth_button', 'n_clicks'),
                        Input('analyze_line_selection_button', 'n_clicks'),
                        Input('wavelength-unit', 'value'),
                        Input('flux-unit', 'value'),
                        Input('wavelength_binning_button', 'n_clicks'),
                        Input('model_fit_button', 'n_clicks'),
                        Input('show_model_button', 'n_clicks'),
                        Input('show_sky_button', 'n_clicks'),
                        Input('show_visits_button', 'n_clicks'),
                        Input('save-trace-changes-button', 'n_clicks'),
                        Input('url', 'search'),
                        Input('search_spectrum_button', 'n_clicks'),
                        Input('load_example_button', 'n_clicks'),
                        Input('spec-graph', 'selectedData'),
             ]

        state_list = [
                        State('upload-data', 'filename'),
                        State('upload-data', 'last_modified'),
                        State('session-id', 'children'),
                        State('dropdown-for-traces', 'value'),
                        State('wavelength_binning_window', 'value'),
                        State('smoothing_kernels_dropdown', 'value'),
                        State('kernel_width_box', 'value'),
                        State('dropdown_for_regions', 'value'),
                        State('add_smoothing_as_trace_checklist', 'value'),
                        State('fitting-model-dropdown', 'value'),
                        State('median_filter_width', 'value'),
                        State('add_fit_subtracted_trace_checklist', 'value'),
                        State('remove_children_checklist', 'value'),
                        State("specid", "value"),
                        State("catalogs-dropdown", "value"),
                        State("traces_table", 'data'),
                    ]

        if self.as_website:
            state_list = state_list + [State('store', 'data')]

        def data_callback(pull_trigger_value,n_clicks_remove_trace_button, list_of_contents, n_clicks_smooth_button,
                          n_clicks_smooth_subtract_button, nclicks_analyze_line_selection_button,
                          n_clicks_unsmooth_button, wavelength_unit, flux_unit, nclicks_wavelength_binning_button,
                          n_clicks_model_fit_button, show_model_button, show_sky_button, show_visits_button,
                          save_trace_changes_button,
                          url_search_string, n_clicks_specid_button, nclicks_load_example_button,selected_data,
                          #states:
                          list_of_names, list_of_dates,
                          session_id, dropdown_trace_names, wavelength_binning_window,
                          smoothing_kernel_name, smoothing_kernel_width, dropdown_for_region_values,
                          add_smoothing_as_trace_checklist, fitting_models, median_filter_width,
                          add_fit_subtracted_trace_checklist, remove_children_checklist, specid,
                          catalog_dropdown_value, traces_table_data, data=None,
                          ):

            task_name = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
            logged_metadata = LoggedMetadata()
            logged_metadata['session_id'] = session_id
            logged_metadata['task_name'] = task_name

            try:
                _data_dict = no_update
                _graph_settings = self._build_graph_settings(axis_units_changed=False)
                _info_message = no_update
                trace_output = [no_update for i in range(max_num_traces)]
                zdist_output = [no_update for i in range(max_num_traces)]

                if not self.as_website:
                    data_dict = self.app_data
                else:
                    data_dict = data if data is not None else self._build_app_data()

                if self.as_website:
                    if len(data_dict['trace_store_mapping']) == 0:
                        self._build_trace_store_mapping(data_dict)
                    if len(data_dict['zdist_store_mapping']) == 0:
                        self._build_zdist_store_mapping(data_dict)

                if task_name == "pull_trigger":
                    if pull_trigger_value == "":
                        pass
                    else:
                        _data_dict = data_dict

                elif task_name == "upload-data" and list_of_contents is not None:
                    if len(list_of_names) == 1 and list_of_names[0].endswith('.json'):
                        content_type, content_string = list_of_contents[0].split(',')
                        decoded_bytes = base64.b64decode(content_string)
                        _data_dict = json.loads(decoded_bytes)
                    else:
                        new_data_list = [
                            self._parse_uploaded_file(c, n, catalog_name=catalog_dropdown_value,
                                                      wavelength_unit=wavelength_unit, flux_unit=flux_unit) for c, n, d
                            in
                            zip(list_of_contents, list_of_names, list_of_dates)]
                        for traces in new_data_list:
                            for trace in traces:
                                self._set_color_for_new_trace(trace, data_dict)
                                self._add_trace_to_data(data_dict, trace, do_update_client=False)

                        self._set_axis_units(data_dict, wavelength_unit, flux_unit)

                        _data_dict = data_dict
                elif task_name == 'wavelength-unit' or task_name == 'flux-unit':
                    self._rescale_axis(data_dict, to_wavelength_unit=wavelength_unit, to_flux_unit=flux_unit)
                    _graph_settings = self._build_graph_settings(axis_units_changed=True)
                    _data_dict = data_dict

                elif task_name == 'wavelength_binning_button':
                    self._bin_wavelength_axis(dropdown_trace_names, data_dict, wavelength_binning_window,
                                              wavelength_unit, flux_unit, do_update_client=False)
                    _data_dict = data_dict

                elif task_name == "remove_trace_button" and len(dropdown_trace_names) > 0:
                    also_remove_children = True if len(remove_children_checklist) > 0 else False
                    self._remove_traces(dropdown_trace_names, data_dict, do_update_client=False,
                                        also_remove_children=also_remove_children)
                    _data_dict = data_dict

                elif (task_name == "trace_smooth_button" or task_name == 'trace_smooth_subtract_button') and len(
                        dropdown_trace_names) > 0 and len(smoothing_kernel_name) > 0:
                    do_subtract = True if task_name == 'trace_smooth_subtract_button' else False
                    do_add = True if len(add_smoothing_as_trace_checklist) > 0 else False
                    smoother = self._get_smoother(smoothing_kernel_name, smoothing_kernel_width)
                    self._smooth_trace(dropdown_trace_names, data_dict, smoother, do_update_client=False,
                                       do_subtract=do_subtract, as_new_trace=do_add)
                    _data_dict = data_dict

                elif task_name == "trace_unsmooth_button" and len(dropdown_trace_names) > 0:
                    self._unsmooth_trace(dropdown_trace_names, data_dict, do_update_client=False)
                    _data_dict = data_dict

                elif task_name == "analyze_line_selection_button":
                    if selected_data is not None:
                        self._get_line_analysis(dropdown_trace_names, data_dict, selected_data,
                                                dropdown_for_region_values, as_new_trace=False, do_update_client=False)
                        _data_dict = data_dict

                elif task_name == "model_fit_button":
                    if selected_data is None or selected_data == {} or len(fitting_models) == 0 \
                            or len(dropdown_trace_names) == 0 or flux_unit == FluxUnit.AB_magnitude:
                        pass
                    else:
                        # self._fit_model_to_flux(dropdown_trace_names, data_dict, fitting_models, selected_data, do_update_client=False)
                        add_fit_subtracted_trace = True if len(add_fit_subtracted_trace_checklist) > 0 else False
                        model_fitters = [self._get_model_fitter(trace_name, data_dict, fitting_model, selected_data) for
                                         trace_name in dropdown_trace_names for fitting_model in fitting_models]
                        _ = self._fit_model_to_flux(dropdown_trace_names, data_dict, model_fitters, selected_data,
                                                    median_filter_width=median_filter_width, do_update_client=False,
                                                    add_fit_subtracted_trace=add_fit_subtracted_trace)
                        _data_dict = data_dict

                elif task_name == "show_model_button":
                    if len(dropdown_trace_names) > 0:
                        self._toggle_derived_traces(SpectrumType.MODEL, dropdown_trace_names, data_dict,
                                                    do_update_client=False)
                        _data_dict = data_dict
                    else:
                        pass

                elif task_name == "show_sky_button":
                    if len(dropdown_trace_names) > 0:
                        self._toggle_derived_traces(SpectrumType.SKY, dropdown_trace_names, data_dict,
                                                    do_update_client=False)
                        _data_dict = data_dict

                elif task_name == "show_visits_button":
                    if len(dropdown_trace_names) > 0:
                        self._toggle_derived_traces(SpectrumType.VISIT, dropdown_trace_names, data_dict,
                                                    do_update_client=False)
                        _data_dict = data_dict

                elif task_name == "spec-graph":
                    if not self.as_website:
                        data_dict['selection'] = self._get_selection(selected_data, data_dict)
                        self.app_data = data_dict
                        _data_dict = no_update

                elif task_name == "url":
                    if self.as_website is True and url_search_string is not None and url_search_string != "":
                        url_search_string = url_search_string[1:] if url_search_string.startswith(
                            "?") else url_search_string
                        specid = None
                        catalog_name = None
                        for (parameter, value) in parse_qsl(url_search_string):
                            if parameter == "specid":
                                specid = value
                            if parameter == "catalog":
                                catalog_name = value
                        if specid is not None and catalog_name is not None:
                            # delete all previous data
                            trace_names = [x for x in data_dict['traces']]
                            self._remove_traces(trace_names, data_dict, do_update_client=False,
                                                also_remove_children=True)
                            # parse and load specids
                            self._load_from_specid_text(specid, wavelength_unit, flux_unit, data_dict,
                                                        catalog_name=catalog_name, do_update_client=False)
                            _data_dict = data_dict

                elif task_name == "search_spectrum_button" or task_name == "load_example_button":
                    if task_name == "load_example_button":
                        specid = example_specids[catalog_dropdown_value]

                    if specid is not None and len(specid) > 0:
                        self._load_from_specid_text(specid, wavelength_unit, flux_unit, data_dict,
                                                    catalog_dropdown_value)
                        _data_dict = data_dict

                elif task_name == "save-trace-changes-button":
                    props = ['rank', 'name', 'color', 'is_visible', 'ancestors', "linewidth"]
                    properties_list = []
                    for trace_data in traces_table_data:
                        row = {prop: trace_data[prop] for prop in props}
                        row['is_visible'] = True if row['is_visible'] == 'true' or row['is_visible'] is True else False
                        ancestors = row['ancestors'].strip('][').replace(" ", "")
                        row['ancestors'] = [] if ancestors == "" else ancestors.split(',')
                        properties_list.append(row)

                    self._update_trace_properties(data_dict, properties_list, do_update_client=False,also_remove_children=False)
                    _data_dict = data_dict


                if _data_dict != no_update:

                    trace_output = self._get_returned_store_traces(_data_dict)
                    zdist_output = self._get_returned_store_zdists(_data_dict)
                    self._initialize_updates(_data_dict) # this will reset all updated since the transaction if now almost completed
                    logged_metadata['info2'] = "ded 3" + str(_data_dict['updates'])

                    if self.as_website:
                        pass
                    else:
                        self._synch_data(_data_dict, self.app_data)
                        _data_dict = self.app_data.copy()

                    _data_dict["traces"] = {}
                    _data_dict["redshift_distributions"] = {}

                logged_metadata['search_string'] = url_search_string
                logged_metadata['specid'] = specid

                return [_data_dict, _graph_settings, _info_message] + trace_output + zdist_output

            except Exception as e:
                exs = str(e)
                logged_metadata.exception = e
                return [no_update, no_update, {'header': "Error", "body": exs}] + trace_output + zdist_output

            finally:
                try:
                    log_message(request=request, logged_metadata=logged_metadata, do_log=do_log)
                except Exception as ex:
                    pass

        if self.as_website:
            @self.app.callback(output_list,input_list,state_list, prevent_initial_callbacks=True)
            def server_side_data_callback(*args):
                return data_callback(*args)
        else:
            @self.app.callback(output_list,input_list, state_list, prevent_initial_callbacks=True)
            def server_side_data_callback(*args):
                return data_callback(*args)

    except:
        pass
