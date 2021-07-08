from specdash import Viewer
from specdash.config import PORT, DEBUG

if __name__ == '__main__':
    viewer = Viewer(as_website=True)
    viewer.app.run_server(port=PORT, debug=DEBUG, dev_tools_ui=True, dev_tools_silence_routes_logging=True)
    # https://dash.plotly.com/devtools
