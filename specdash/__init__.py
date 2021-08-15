from specdash.config import CATALOGS, PORT, LOGS, DASH_TABLE_PAGE_SIZE, DEFAULT_WAVELENGTH_UNIT, DEFAULT_FLUX_UNIT, MAX_NUM_TRACES
#from werkzeug.middleware.dispatcher import DispatcherMiddleware

package_name = __name__

port = PORT
external_stylesheets = ['https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css']
#external_stylesheets = []
external_scripts = ['https://code.jquery.com/jquery-3.5.0.min.js', 'https://cdn.plot.ly/plotly-latest.min.js','https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js','https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML',
                    {
                        "src": "//cdnjs.cloudflare.com/ajax/libs/socket.io/2.2.0/socket.io.js",
                        "integrity": "sha256-yr4fRk/GU1ehYJPAs8P4JlTgu0Hdsp4ZKrx8bDEDC3I=",
                        "crossorigin": "anonymous",
                    }
                    ]
#external_scripts = []
#server = flask.Flask(__name__) # define flask app.server
#app = dash.Dash(__name__, external_stylesheets=external_stylesheets, external_scripts=external_scripts, server=server,  requests_pathname_prefix='/specdash/')

#app.scripts.append_script({"external_url": 'https://code.jquery.com/jquery-3.5.0.min.js'})
#app.layout = html.Div([dcc.Interval(id='interval-component',interval=1*1000,n_intervals=0),html.Div(className='row', children=[html.Div(id='live-update-text')])])

# Check base data directories containing spectra from defined catalogs
do_log = LOGS.get("do_log")
base_logs_directory = LOGS.get("base_logs_directory")
base_data_directories = { catalog: CATALOGS[catalog]['base_data_path'] if CATALOGS[catalog]['base_data_path'].endswith("/")
                            else CATALOGS[catalog]['base_data_path'] + "/" for catalog in CATALOGS }
api_urls = { catalog: CATALOGS[catalog]['api_url'] for catalog in CATALOGS }
example_specids = { catalog: CATALOGS[catalog]['example_specid'] for catalog in CATALOGS }

catalog_names = [catalog for catalog in CATALOGS]

dash_table_page_size = DASH_TABLE_PAGE_SIZE
default_wavelength_unit = DEFAULT_WAVELENGTH_UNIT
default_flux_unit = DEFAULT_FLUX_UNIT
max_num_traces = int(MAX_NUM_TRACES)

# Import Spectrum Viewer class
from specdash.viewer import Viewer