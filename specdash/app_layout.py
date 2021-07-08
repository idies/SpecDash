from specdash import max_num_traces
from specdash.models.data_models import WavelengthUnit, FluxUnit
from specdash import catalog_names, default_wavelength_unit, default_flux_unit
import dash_core_components as dcc
import dash_daq as daq
from specdash.layout.tables import get_dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
from dash_extensions import Download
from textwrap import dedent as d
from .spectral_lines import spectral_lines, sky_lines, artificial_lines
import json
from specdash.models.enum_models import SpectrumType
from specdash.smoothing.smoother import default_smoothing_kernels, SmoothingKernels
from specdash.fitting.fitter import default_fitting_models, FittingModels
from specdash.input import get_supported_catalogs
#from dash_extensions import WebSocket
import uuid
#import sd_material_ui as mui

spectral_line_dropdown_options = [{'label':'all', 'value':'all'}]
spectral_line_dropdown_options = spectral_line_dropdown_options + [ {'label':spectral_lines[line]['fullname'], 'value':spectral_lines[line]['fullname']} for line in spectral_lines]
sky_line_dropdown_options = [{'label':'all', 'value':'all'}]
sky_line_dropdown_options = sky_line_dropdown_options + [ {'label':sky_lines[line]['fullname'], 'value':sky_lines[line]['fullname']} for line in sky_lines]
artificial_line_dropdown_options = [{'label':'all', 'value':'all'}]
artificial_line_dropdown_options = artificial_line_dropdown_options + [ {'label':artificial_lines[line]['fullname'], 'value':artificial_lines[line]['fullname']} for line in artificial_lines]
dash_table_page_size = 5



smoothing_kernel_options = [{'label':type, 'value':type} for type in default_smoothing_kernels]
fitting_model_options = [{'label':type, 'value':type} for type in default_fitting_models]
supported_catalog_options = [{'label':catalog, 'value':catalog} for catalog in catalog_names]


# docs:
# https://dash-bootstrap-components.opensource.faculty.ai/
# https://github.com/ucg8j/awesome-dash#component-libraries
# https://pypi.org/project/dash-database/
# https://github.com/thedirtyfew/dash-extensions/
# https://github.com/ucg8j/awesome-dash
# https://github.com/richlegrand/dash_devices
# https://github.com/GibbsConsulting/django-plotly-dash
# https://gitlab.com/pgjones/quart

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}


def get_navbar():
    navbar = dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("About", href="#")),
            dbc.NavItem(dbc.NavLink("Docs", href="/docs")),
        ],
        brand="Spectrum Viewer",
        brand_href="/",
        color="blue",
        dark=False
    )
    return navbar


def get_spectrum_page_layout(self):
    storage_mode = self.storage_mode

    layout = html.Div([
        # The local store will take the initial data only the first time the page is loaded
        # and keep it until it is cleared.
        # dcc.Store(id='store', storage_type='memory'),
        # Same as the local store but will lose the data when the browser/tab closes.
        html.Div(style={"display": "none"}, children=[
            dcc.Store(id='graph-settings', storage_type=storage_mode),
            dcc.Store(id='graph_trace_info', storage_type=storage_mode),
            dcc.Store(id='info-message', storage_type=storage_mode),
            # stores the URL of the page plus query string
            dcc.Location(id='url', refresh=False),
            # https://dash.plotly.com/dash-core-components/input
            dcc.Input(id="pull_trigger", type="text", value="dwdww", style={'visibility': 'hidden'}),
            html.Div(style={"display": "none"},
                     children=[dcc.Store(id='trace_' + str(i), storage_type=storage_mode) for i in
                               range(max_num_traces)]),
            html.Div(style={"display": "none"},
                     children=[dcc.Store(id='zdist_' + str(i), storage_type=storage_mode) for i in
                               range(max_num_traces)]),
            dcc.Input(id="max_num_traces", type="number", value=max_num_traces, style={'visibility': 'hidden'}),

        ]),

        html.Div(id="top-container", className="container", style={'minWidth':'100%'}, children=[
            html.Div(id="top-panel-div", className="row", style={}, children=[
                ## first column --------------------------------------------------------------------------------------------

                html.Div(id="top-panel-div1", className="col-sm-2", style={'backgroundColor':"#F8F8F8"}, children=[
                    html.Br(),
                    html.Div(id="divid", className="row", style={}, children=[
                        html.Div(id="fewfe", className="col-sm-8 ", style={}, children=[
                            dbc.Button(outline=True, color="success", className="",
                                style={'fontWeight': 'bold','width':'100%'}, id="open-loadingmodal-button", children=[
                                    "Load Data",
                                ]),
                        ]),
                        html.Div(id="store-div", className="col-sm-4 ", style={}, children=[
                            #dbc.Spinner(
                            dcc.Loading(
                                id="loading-1",
                                #size="md",
                                # type="default",
                                # className="data-loading",
                                # parent_className="loading-parent",
                                children=[dcc.Store(id='store_intermediate', storage_type=storage_mode), dcc.Store(id='store', storage_type=storage_mode)],
                                # style={"float": "right"},
                                # fullscreen=True,
                                #color="blue",
                                #spinner_style={'display': 'inline', 'justify-content': 'right', 'align-items': 'right'},
                            ),
                        ]),
                    ]),
                    dbc.Modal(id="load-spectra-modal",size="lg",children=[
                        dbc.ModalHeader(children=[
                            html.Div(children=["Load Data"], style={'align': 'center'}),
                        ]),
                        dbc.ModalBody(children=[
                            html.Div(className="row", children=[
                                html.Div(className="col-sm-1", children=[
                                    html.Div([
                                        "Catalog:"
                                    ])
                                ]),
                                html.Div(className="col-sm-3", children=[
                                    dcc.Dropdown(
                                        id='catalogs-dropdown',
                                        options=supported_catalog_options,
                                        value=catalog_names[0],
                                        placeholder="select catalog...",
                                        multi=False,
                                        clearable=False,
                                        style={},
                                        persistence="true",
                                        persisted_props=["value"],
                                        persistence_type=storage_mode
                                    ),
                                ]),
                                html.Div(className="col-sm-3", children=[
                                    dbc.Button("Load example", color="success", outline=True,
                                               className="btn btn-md ml-2",
                                               style={"width": "90%"}, id="load_example_button"),
                                ]),
                            ]),
                            html.Br(),
                            html.Div(className="row", children=[
                                html.Div(className="col-sm-9", children=[
                                    dcc.Textarea(id="specid",
                                                 placeholder="Enter spectrum IDs (as a column, or separated by a | character)",
                                                 autoFocus='true',
                                                 persistence=True,
                                                 persistence_type=storage_mode,
                                                 value="",
                                                 className="",
                                                 style={}
                                                 ),
                                ]),
                                html.Div(className="col-sm-3", children=[
                                    dbc.Button("Load", color="success", outline=True,
                                               className="btn btn-md ml-2",
                                               style={"width": "100%"}, id="search_spectrum_button"),
                                ]),
                            ]),
                            html.Br(),
                            html.Br(),
                            dcc.Upload(id='upload-data', className="upload scaled", children=html.Div([
                                'Upload fits file(s) or json dump'
                            ]),
                                       style={
                                           'width': '50%',
                                           'height': '4em',
                                           'lineHeight': '60px',
                                           'borderWidth': '1px',
                                           'borderStyle': 'dashed',
                                           'borderRadius': '5px',
                                           'textAlign': 'center',
                                           'margin': '5px'
                                       },
                                       multiple=True  # Allow multiple files to be uploaded
                                       ),

                        ]),
                        dbc.ModalFooter(
                            dbc.Button("Close", color="secondary", outline=True,
                                       className="btn btn-md ml-2",
                                       style={}, id="close-loadingmodal-button"),
                        ),
                    ]),
                    dbc.Modal(id="info-modal",size="lg",is_open=False,children=[
                            dbc.ModalHeader(id="info-modal-header", children=[]),
                            dbc.ModalBody(id="info-modal-body", children=[]),
                            dbc.ModalFooter(
                                dbc.Button("Close", color="secondary", outline=True,
                                           className="btn btn-md ml-2",
                                           style={}, id="close-infomodal-button"),
                            ),
                    ]),
                    dbc.Modal(id="list-traces-modal",size="xl",style={'minWidth':'90%'}, is_open=False,children=[
                        dbc.ModalHeader(id="traces-modal-header", children=['Loaded Traces']),
                        dbc.ModalBody(id="traces-modal-body", children=[
                            html.Div(className="container",style={"minWidth":"100%"},children=[
                                html.Div(className="row", children=[
                                    html.Div(className="col-md-9", children=[
                                        html.Div(style={'height': '30rem', 'overflowY': 'auto'}, children=[
                                            get_dash_table(id_prefix="traces_table", hidden_columns=['rank'],
                                                           row_deletable=True),
                                        ]),
                                    ]),
                                    html.Div(className="col-md-3", style={}, children=[
                                        daq.ColorPicker(id="color_picker", label="", style={"width":"100%"},
                                                        value=dict(rgb=dict(r=255, g=0, b=0, a=0))),
                                    ]),

                                ]),
                            ]),
                        ]),
                        dbc.ModalFooter(children=[
                            dbc.Button('save', color="primary", outline=True,
                                       className="btn btn-md ml-2",
                                       id='save-trace-changes-button'),
                            dbc.Button("close", color="secondary", outline=True,
                                       className="btn btn-md ml-2",
                                       style={}, id="close-tracesmodal-button"),

                        ]),
                    ]),
                    html.Div(className="ml-1", children=[

                        html.Hr(),
                        dbc.Button("Edit traces", color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton", id="open-list-traces-button", style={}),
                        html.Hr(),

                        html.H6(["Active traces:"]),
                        html.Div(id="trace-dropdown-div", children=[
                            dcc.Dropdown(
                                id='dropdown-for-traces',
                                options=[],  # [{'label': label, 'value': label} for label in labels],
                                # options=[{'label': label, 'value': label} for label in labels],
                                value=[],
                                placeholder="select...",
                                multi=True,
                                style={'fontSize': 'small','minWidth':'100%'},
                                optionHeight=65,
                                # sets the height of each selection row (to be able to read the names)
                                persistence="true",
                                persisted_props=["value"],
                                persistence_type=storage_mode
                            )
                        ]),
                        html.Br(),
                        dbc.Button("select all/none", color="primary", outline=True,
                           className="btn btn-sm m-1 specbutton",id="select_all_traces_button"),
                        dbc.Button("remove", color="primary", outline=True,
                           className="btn btn-sm m-1 specbutton",id="remove_trace_button"),
                        html.Br(),
                        dcc.Checklist(
                            id="remove_children_checklist",
                            options=[
                                {'label': 'remove derived traces', 'value': 'remove_children'},
                            ],
                            value=['remove_children'],  # 'add_model'
                            labelStyle={'display': 'inline-block'},
                            persistence=True,
                            persistence_type=storage_mode,
                            persisted_props=["value"],
                        ),
                        html.Hr(),
                        html.H6(["Toggle:"]),
                        dbc.Button('model', color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_model_button'),
                        dbc.Button('sky', color="primary", outline=True, className="btn btn-sm m-1 specbutton",
                                   id='show_sky_button'),
                        dbc.Button('error', color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_error_button'),
                        dbc.Button('photo', color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_photometry_button'),
                        dbc.Button('visits', color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_visits_button'),
                        dbc.Button('bar plot', color="primary", outline=True,
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_barchart_button'),
                        dbc.Button('redshift PDF', color="primary", outline=True, style={'display': 'none'},
                                   className="btn btn-sm m-1 specbutton",
                                   id='show_zdist_button'),
                        html.Hr(),
                        html.Br(),
                        html.P("Help: mtaghiza [at] jhu.edu"),
                        html.Br(),
                        # html.Div(dcc.Input(style={'display':'none'}, id='input-box', type='text', value="")),
                        html.Button('Submit', id='button', style={'display': 'none'}),
                        html.Br(),
                        html.Div(id='output-container-button', style={'display': 'none'},
                                 children='Enter a value and press submit'),

                    ]),

                ]),

                ## next column --------------------------------------------------------------------------------------------
                html.Div(id="top-panel-div2", className="col-sm-10", style={}, children=[

                     html.Div(id="c1", style={'minWidth': "99%", 'height': "50vh", "resize": 'vertical', 'overflow': 'hidden'}, children=[
                         dcc.Graph(
                            id='spec-graph',
                            # figure=self.spec_figure,
                            figure={},
                            style={'height':"100%", "width":"99%"},
                            config={'displayModeBar': True, 'scrollZoom': True, 'responsive': True,'displaylogo': False},
                         ),
                    ]),

                    html.Div(style={'minHeight':'50vh'},children=[
                        html.Hr(className="tab-hr"),
                        dcc.Tabs(id="tabs", parent_className='custom-tabs', className='custom-tabs-container',
                            value="data", style={'width': '100%'}, persistence=True,mobile_breakpoint=400,
                            persistence_type=storage_mode, children=[
                            dcc.Tab(id="metadata", className="custom-tab", selected_className='custom-tab-selected',
                                label="Data", value="data", children=[
                                html.Hr(className="tab-hr"),
                                dcc.Tabs(id="data-tabs", parent_className='custom-tabs',mobile_breakpoint=400,
                                    className='custom-tabs-container', value='info-tab', children=[
                                        dcc.Tab(id="info-tab", label="Info", className="custom-subtab",
                                            selected_className='custom-subtab-selected', value="info-tab",
                                            children=[
                                                html.Br(),
                                                dcc.Markdown(id="info_content", children=[''],
                                                             dangerously_allow_html=True),
                                        ]),
                                        dcc.Tab(id="data-download-tab", label="Download",
                                                className="custom-subtab",
                                                selected_className='custom-subtab-selected', value="download-tab",
                                                children=[
                                                    html.Br(),
                                                    'Save data as json dump.',
                                                    html.Div([dbc.Button("Download", id="download-button",
                                                                         color="primary", outline=True,
                                                                         className="btn btn-sm m-1 specbutton"),
                                                              Download(id="download-file")]),
                                                ]),
                                        dcc.Tab(id="data-selection-tab", label="Selection",
                                                className="custom-subtab",
                                                selected_className='custom-subtab-selected', value="selection-tab",
                                                children=[
                                                    html.Br(),
                                                    html.Label('Selected data points:'),
                                                    get_dash_table(id_prefix="current_data_selection_table"),
                                        ]),

                                    ]),
                            ]),
                            dcc.Tab(label="Axis", className="custom-tab", selected_className='custom-tab-selected',
                                value="axisunits", children=[
                                html.Hr(className="tab-hr"),
                                html.Br(),
                                html.Div(className="row", children=[
                                    html.Div(className="col-sm-auto", children=[
                                        html.Span(["Wavelength:"]),
                                        dcc.Dropdown(
                                            id='wavelength-unit',
                                            options=[{'label': "nanometer", 'value': WavelengthUnit.NANOMETER},
                                                     {'label': "Angstrom", 'value': WavelengthUnit.ANGSTROM}],
                                            value=default_wavelength_unit,
                                            placeholder="Wavelength unit",
                                            multi=False,
                                            style={"minWidth": "10rem"},
                                            clearable=False,
                                            persistence=True,
                                            persistence_type=storage_mode,
                                        ),
                                    ]),
                                    html.Div(className="col-sm-auto", children=[
                                        html.Span(["Flux:"]),
                                        dcc.Dropdown(
                                            id='flux-unit',
                                            options=[
                                                {'label': "erg/s/cm^2/A", 'value': FluxUnit.F_lambda},
                                                {'label': "erg/s/cm^2/Hz", 'value': FluxUnit.F_nu},
                                                {'label': "Jansky", 'value': FluxUnit.Jansky},
                                                {'label': "AB Magnitude", 'value': FluxUnit.AB_magnitude}
                                            ],
                                            value=default_flux_unit,
                                            placeholder="Flux unit",
                                            multi=False,
                                            style={"minWidth": "10rem"},
                                            clearable=False,
                                            persistence=True,
                                            persistence_type=storage_mode,
                                        ),
                                    ]),
                                ]),
                            ]),
                            dcc.Tab(label="Lines", className="custom-tab", selected_className='custom-tab-selected',
                                value="speclines", style={}, children=[
                                html.Hr(className="tab-hr"),
                                dcc.Tabs(id="speclines-tabs", parent_className='custom-tabs',
                                className='custom-tabs-container', value='speclines-display',mobile_breakpoint=400,
                                children=[
                                    dcc.Tab(id="speclines-display", label="Display",
                                        className="custom-subtab",
                                        selected_className='custom-subtab-selected',
                                        value="speclines-display", children=[
                                        html.Br(),
                                        html.Div(className="container-fluid", style={'minWidth':"99%"}, children=[
                                            html.Div(className="row", children=[
                                                html.Div(className="col-sm-auto", children=[
                                                    html.Div(className="container", children=[
                                                        html.Div(className="row", children=[
                                                            html.Div(className="col-sm-auto", children=[
                                                                'Spectral:',
                                                                html.Br(),
                                                                dcc.Dropdown(
                                                                    id='spectral_lines_dropdown',
                                                                    placeholder="select...",
                                                                    options=spectral_line_dropdown_options,
                                                                    value=[],
                                                                    multi=True,
                                                                    style={"width": "25rem", 'float': 'left'},
                                                                    clearable=True
                                                                ),
                                                                daq.BooleanSwitch(
                                                                    id="spectral-lines-switch",
                                                                    on=True,
                                                                    persistence=True,
                                                                    persistence_type=storage_mode,
                                                                    style={'float': 'left',
                                                                           'paddingLeft': '1em'},
                                                                ),
                                                            ]),
                                                        ]),
                                                        html.Div(className="row", children=[
                                                            html.Div(className="col-sm-auto", children=[
                                                                'Sky:',
                                                                html.Br(),
                                                                dcc.Dropdown(
                                                                    id='sky_lines_dropdown',
                                                                    placeholder="select...",
                                                                    options=sky_line_dropdown_options,
                                                                    value=[],
                                                                    multi=True,
                                                                    style={"width": "25rem", 'float': 'left'},
                                                                    clearable=True
                                                                ),
                                                                daq.BooleanSwitch(
                                                                    id="sky-lines-switch",
                                                                    on=True,
                                                                    persistence=True,
                                                                    persistence_type=storage_mode,
                                                                    style={'float': 'left',
                                                                           'paddingLeft': '1em'},
                                                                ),

                                                            ]),
                                                        ]),
                                                        html.Div(className="row", children=[
                                                            html.Div(className="col-sm-auto", children=[
                                                                'Artificial:',
                                                                html.Br(),
                                                                dcc.Dropdown(
                                                                    id='artificial_lines_dropdown',
                                                                    placeholder="select...",
                                                                    options=artificial_line_dropdown_options,
                                                                    value=[],
                                                                    multi=True,
                                                                    style={"width": "25rem", 'float': 'left'},
                                                                    clearable=True
                                                                ),
                                                                daq.BooleanSwitch(
                                                                    id="artificial-lines-switch",
                                                                    on=True,
                                                                    persistence=True,
                                                                    persistence_type=storage_mode,
                                                                    style={'float': 'left',
                                                                           'paddingLeft': '1em'},
                                                                ),
                                                            ]),
                                                        ]),
                                                    ]),
                                                ]),
                                                html.Div(className="col-sm-auto", children=[
                                                    html.Div(className="container", children=[
                                                        #html.H6("Redshift"),
                                                        html.Div(className="row",children=[
                                                            html.Div(className="col-sm-auto",children=[
                                                                "Custom redshift:",
                                                                html.Br(),
                                                                dcc.Input(
                                                                    id='redshift_input',value='0',type='number',inputMode="numeric",style={})
                                                            ]),
                                                            html.Div(className="col-sm-auto",style={"paddingLeft": "2em"},children=[
                                                                html.Br(),
                                                                html.Br(),
                                                                daq.Slider(id="redshift-slider",min=0,max=4,value=0,marks={i:i for i in range(0, 4 + 1)},
                                                                    handleLabel={"showCurrentValue": True,"label": "Redshift"},step=0.01,className="slider",size=400, updatemode="drag"),
                                                            ]),
                                                        ]),
                                                        html.Br(),
                                                        html.Div(className="row", children=[
                                                            html.Div(className="col-sm-auto", children=[
                                                                "from object:",
                                                                html.Br(),
                                                                dcc.Dropdown(
                                                                    id='redshift-dropdown',
                                                                    options=[],
                                                                    # [{'label': label, 'value': label} for label in labels],
                                                                    # options=[{'label': label, 'value': label} for label in labels],
                                                                    value=[],
                                                                    placeholder="",
                                                                    multi=False,
                                                                    style={
                                                                        'fontSize': 'small',
                                                                        'minWidth': "35rem"},
                                                                    optionHeight=65,
                                                                    # sets the height of each selection row (to be able to read the names)
                                                                    persistence="true",
                                                                    persisted_props=[
                                                                        "value"],
                                                                    clearable=True,
                                                                    persistence_type=storage_mode
                                                                ),
                                                            ]),

                                                        ]),

                                                    ]),
                                             ]),
                                            ]),
                                        ]),
                                    ]),
                                    dcc.Tab(id="speclines-analysis", label="Analysis",
                                            className="custom-subtab",
                                            selected_className='custom-subtab-selected',
                                            value="speclines-analysis", children=[
                                            html.Br(),
                                            html.Div(className="container", style={'minWidth': '98%'}, children=[
                                                html.Div(className="row",children=[
                                                    html.Div(className="col-sm-4",children=[
                                                        html.Label('Select line with lasso or box in top-right menu.'),
                                                        html.Br(),
                                                        "Continuum:",
                                                        html.Br(),
                                                        dcc.Dropdown(
                                                            id='dropdown_for_regions',
                                                            options=[],
                                                            value=[],
                                                            placeholder="select...",
                                                            multi=False,
                                                            # style={'fontSize': 'small'},
                                                            optionHeight=65,
                                                            persistence=True,
                                                            persistence_type=storage_mode,
                                                            style={'minWidth':"25rem", "maxWidth":"30rem",'float':'left'},
                                                        ),
                                                        html.Br(),
                                                        dbc.Button("Analize Line", color="primary", outline=True,
                                                                   className="btn btn-md m-1 specbutton",
                                                                   id="analize_line_selection_button",
                                                                   style={}),



                                                    ]),
                                                    html.Div(className="col-sm-8", children=[
                                                        html.Label("Measured lines:"),
                                                        get_dash_table(id_prefix="line_analysis_table"),

                                                    ]),

                                                ]),
                                            ]),
                                        ]),
                                    dcc.Tab(id="speclines-from-dataset", label="From dataset",
                                        className="custom-subtab",
                                        selected_className='custom-subtab-selected',
                                        value="speclines-from-dataset", children=[
                                             html.Br(),
                                             html.Div(className="container", style={'minWidth': '98%'},children=[
                                                  get_dash_table(id_prefix="measured_lines_table",
                                                                 fixed_columns={'headers': True,'data': 2}),
                                                  html.Br(),
                                                  dcc.Markdown(id="spectral_lines_info",
                                                               children=[''],
                                                               dangerously_allow_html=True),
                                                  html.Div(dcc.Input(id='spectral_lines_dict',
                                                                     value=json.dumps(
                                                                         spectral_lines),
                                                                     style={
                                                                         'display': 'none'})),
                                                  html.Div(dcc.Input(id='sky_lines_dict',
                                                                     value=json.dumps(
                                                                         sky_lines),
                                                                     style={
                                                                         'display': 'none'})),
                                                  html.Div(dcc.Input(id='artificial_lines_dict',
                                                                     value=json.dumps(
                                                                         artificial_lines),
                                                                     style={
                                                                         'display': 'none'})),

                                        ]),
                                    ]),

                                ]),
                            ]),




                            dcc.Tab(label="Masks", className="custom-tab", selected_className='custom-tab-selected',
                                value="masks", children=[
                                html.Hr(className="tab-hr"),
                                html.Br(),
                                html.Div(className="row", children=[
                                    html.Div(className="col-sm-10", children=[
                                        dcc.Dropdown(
                                            id='dropdown-for-masks',
                                            options=[],
                                            # [{'label': label, 'value': label} for label in labels],
                                            value=[],
                                            placeholder="select mask(s)...",
                                            multi=True,
                                            # style={'fontSize': 'small'},
                                            optionHeight=65,
                                            persistence=True,
                                            persistence_type=storage_mode
                                        ),
                                    ]),
                                    html.Div(className="col-sm-1", children=[
                                        daq.BooleanSwitch(id="mask_switch",
                                                          on=True,
                                                          label="on/off",
                                                          labelPosition="bottom",
                                                          persistence=True,
                                                          persistence_type=storage_mode,
                                                          ),
                                    ]),
                                ]),

                            ]),
                            dcc.Tab(label="Modeling", className="custom-tab",
                            selected_className='custom-tab-selected', value="modeling", style={}, children=[
                            html.Hr(className="tab-hr"),
                            dcc.Tabs(id="fitmodels-tabs", parent_className='custom-tabs',mobile_breakpoint=400,
                                className='custom-tabs-container', value='fitting', children=[
                                    dcc.Tab(id="fitting-models-tab", label="Fitting", value="fitting",
                                            className="custom-subtab",
                                            selected_className='custom-subtab-selected', children=[
                                            html.Br(),
                                            html.Div(className="row", children=[
                                                html.Div(className="col-sm-12", children=[

                                                    html.Div(["Select data with lasso or box in top-right menu."]),
                                                    dcc.Dropdown(
                                                        id='fitting-model-dropdown',
                                                        options=fitting_model_options,
                                                        # value=[FittingModels.GAUSSIAN_PLUS_LINEAR],
                                                        value=[],
                                                        placeholder="Select model(s)...",
                                                        multi=True,
                                                        style={"maxWidth": "30rem"},
                                                        persistence=True,
                                                        persistence_type=storage_mode
                                                    ),
                                                    html.Br(),
                                                    "Pre-apply median filter:",
                                                    html.Br(),
                                                    dcc.Input(id='median_filter_width', value=None, type='number', placeholder="window width"),
                                                    html.Br(),
                                                    html.Br(),
                                                    dbc.Button('Fit model(s)', color="primary", outline=True,
                                                               className="btn btn-md m-1 specbutton",
                                                               id='model_fit_button'),
                                                    html.Br(),
                                                    dcc.Checklist(
                                                        id="add_fit_substracted_trace_checklist",
                                                        options=[
                                                            {'label': 'add fit-subtracted trace',
                                                             'value': 'add_fit_substracted_trace'},
                                                        ],
                                                        value=[],  # ['add_smoothed_as_trace']
                                                        labelStyle={'display': 'inline-block'},
                                                        persistence=True,
                                                        persistence_type=storage_mode,
                                                        persisted_props=["value"],
                                                    ),

                                                ]),
                                            ]),

                                    ]),
                                    dcc.Tab(id="fitted-models-tab", label="Fitted Models",
                                        className="custom-subtab",
                                        selected_className='custom-subtab-selected', value="fitted models",
                                        children=[

                                            html.Br(),
                                            html.Div(className="container", style={'maxWidth': '96%'},
                                                 children=[
                                                     get_dash_table(id_prefix='fitted_models_table')
                                                 ]),

                                    ]),
                                    dcc.Tab(label="Smoothing", className="custom-subtab",
                                            selected_className='custom-subtab-selected', value="smoothing", children=[
                                            html.Br(),
                                            html.Div(className="row", children=[
                                                html.Div(className="col-sm-2", children=[
                                                    html.Span(["Kernel:"]),
                                                    dcc.Dropdown(
                                                        id='smoothing_kernels_dropdown',
                                                        # options=[{'label': "Gaussian", 'value': "Gaussian1DKernel"},
                                                        #         {'label': "Box", 'value': "Box1DKernel"}],
                                                        options=smoothing_kernel_options,
                                                        value=SmoothingKernels.MEDIAN,
                                                        placeholder="select...",
                                                        multi=False,
                                                        style={"maxWidth": "15em"},
                                                        clearable=False,
                                                        # persistence=True,
                                                        persistence_type=storage_mode
                                                    )
                                                ]),
                                                html.Div(className="col-sm-2", children=[
                                                    html.Span(["Width:"]),
                                                    html.Div(
                                                        dcc.Input(id='kernel_width_box', value='5', type='number')),
                                                ]),
                                            ]),
                                            html.Br(),
                                            dbc.Button('Smooth', color="primary", outline=True,
                                                       className="btn btn-sm m-1 specbutton", id='trace_smooth_button'),
                                            dbc.Button('Subtract smoothed', color="primary", outline=True,
                                                       className="btn btn-sm m-1 specbutton",
                                                       id='trace_smooth_substract_button'),
                                            dbc.Button('Reset', color="primary", outline=True,
                                                       className="btn btn-sm m-1 specbutton",
                                                       id='trace_unsmooth_button'),
                                            html.Br(),
                                            dcc.Checklist(
                                                id="add_smoothing_as_trace_checklist",
                                                options=[
                                                    {'label': 'add result as new trace', 'value': 'add_as_new_trace'},
                                                ],
                                                value=[],  # ['add_smoothed_as_trace']
                                                labelStyle={'display': 'inline-block'},
                                                persistence=True,
                                                persistence_type=storage_mode,
                                                persisted_props=["value"],
                                            ),

                                        ]),
                                    dcc.Tab(id="binning-tab", label="Binning",
                                            className="custom-subtab",
                                            selected_className='custom-subtab-selected', value="binning",
                                            children=[

                                                html.Br(),
                                                html.Div(className="col-sm-auto", children=[
                                                    html.Span(["Wavelength binning:"]),
                                                    html.Br(),
                                                    dcc.Input(
                                                        id='wavelength_binning_window', value=None, type='number',
                                                        inputMode="numeric", placeholder="bin width..",
                                                        style={}),
                                                    dbc.Button("Create", id="wavelength_binning_button",
                                                               color="primary", outline=True,
                                                               className="btn btn-sm m-1 specbutton")
                                                ]),

                                            ]),

                                ]),
                            ]),
                            dcc.Tab(label="Redshift PDF", className="custom-tab",
                            selected_className='custom-tab-selected', value="zdist", children=[
                                html.Hr(className="tab-hr"),
                                html.Div(className="row", children=[
                                    html.Div(className="col-sm-6", children=[
                                        dbc.Button('Linear/Log', color="primary", outline=True, style={},
                                                   className="btn btn-sm m-1 specbutton",
                                                   id='show_zdistlog_button'),
                                        dcc.Graph(
                                            id='zdist-graph',
                                            # figure=self.spec_figure,
                                            figure={},
                                            # style={"minHeight":"100%"},
                                            config={'displayModeBar': True, 'scrollZoom': True,
                                                    'responsive': True,
                                                    'displaylogo': False},
                                        ),
                                    ]),
                                    html.Div(className="col-sm-6", children=[
                                        html.Br(),
                                        html.Span("Show fitted model:"),
                                        dcc.Dropdown(
                                            id='dropdown-for-specmodels',
                                            options=[],
                                            # [{'label': label, 'value': label} for label in labels],
                                            value='',
                                            placeholder="select...",
                                            multi=True,
                                            persistence=True,
                                            persistence_type=storage_mode,
                                            style={},
                                        ),
                                    ]),

                                ])
                            ]),
                            ]),

                    ]),

                    html.Div(style={'display': 'none'}, children=[
                        # html.Div(style={}, children=[

                        html.Div(className='row', children=[
                            html.Div([
                                dcc.Markdown(d("""
                                    **Hover Data**
                            
                                    Mouse over values in the graph.
                                                                    """)
                                                                     ),
                                                        html.Pre(id='hover-data', style=styles['pre'])
                                                    ], className='three columns'),

                                                    html.Div([
                                                        dcc.Markdown(d("""
                                    **Click Data**
                            
                                    Click on points in the graph.
                                """)),
                                html.Pre(id='click-data', style=styles['pre']),
                            ], className='three columns'),

                            html.Div([
                                dcc.Markdown(d("""
                            **Selection Data**
                    
                            Choose the lasso or rectangle tool in the graph's menu
                            bar and then select points in the graph.
                    
                            Note that if `layout.clickmode = 'event+select'`, selection data also 
                            accumulates (or un-accumulates) selected data if you hold down the shift
                            button while clicking.
                            """)),
                                html.Pre(id='selected-data', style=styles['pre']),
                            ], className='three columns'),

                            html.Div([
                                dcc.Markdown(d("""
                                **Zoom and Relayout Data**
                        
                                Click and drag on the graph to zoom or click on the zoom
                                buttons in the graph's menu bar.
                                Clicking on legend items will also fire
                                this event.
                            """)),
                                 html.Pre(id='relayout-data', style=styles['pre']),
                            ], className='three columns'),
                            html.Div(className='row', children=[
                                html.Div(id='eraseme')
                            ]),
                            html.Div(className='row', children=[
                                html.Div(id='live-update-text')
                            ]),
                            html.Div(className='row', children=[
                                html.Div(id='live-update-text2')
                            ]),
                            html.Div(className='row', children=[
                                html.Div(id='live-update-text3')
                            ])
                        ])

                    ]),

                ]),
                html.Br(),
            ]),
        ]),
    # end layput
    ])

    return layout

def get_documentation_page_layout(self):
    layout =  html.Div(children=[
        html.Br(),
        dbc.Container(children=[
            html.H5("Currently under development."),
            html.H6("Contact: Manuchehr Taghizadeh-Popp, mtaghiza [at] jhu.edu"),
            #html.Iframe(src="https://docs.astropy.org/en/latest/", style={'width':"100%",'height':"95vh"})
        ])
    ])
    return layout

def get_docs_layout():
    layout = html.Div(id="docs-div", children=[
        #html.Div(children=["weew"]),
        html.Iframe(src="/sphinx")
    ])
    return layout

def load_app_layout(self): # self is passed as the Viewer class to fill out the figure element on the
    session_id = str(uuid.uuid4())
    spectrum_layout = get_spectrum_page_layout(self)
    documentation_layout = get_documentation_page_layout(self)

    layout = html.Div([
        html.Div(session_id, id='session-id', style={'display': 'none'}),
        #html.Div(session_id, id='session-id'),
        dbc.Nav(className="", style={'backgroundColor':"#0276FD","height":""},fill=True,children=[

            dbc.NavItem([
                dbc.NavbarBrand(className="", href="/",style={'color':'white','height':''},children=[
                    html.Div("Spectrum Viewer",style={'display':'inline'}),
                ]),
            ], style={}),
            dbc.NavItem([
                dbc.NavLink('Documentation', href='/docs', style={'color': 'white', 'cursor': 'pointer'}),

            ]),
        ]),

        html.Div(
            id='main-page',
            style={'display': 'block'},
            children=[spectrum_layout]
        ),
        html.Div(
            id='docs-page',
            style={'display': 'none'},
            children=[documentation_layout]),
    ])

    return layout
