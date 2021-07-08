PORT = 8050
DEBUG = True
DASH_TABLE_PAGE_SIZE = 5
DEFAULT_WAVELENGTH_UNIT = "angstrom"
DEFAULT_FLUX_UNIT = "F_lambda"
LOGS = { "do_log":True, "base_logs_directory":"/base/logs/directory/" }
MAX_NUM_TRACES = 30
CATALOGS =  {
                "sdss": {
                            "base_data_path":"/base/data/path/",
                            "api_url":"http://skyserver.sdss.org/public/SkyServerWS/SearchTools/SqlSearch",
                            "example_specid":"2947691243863304192"
                        }
            }