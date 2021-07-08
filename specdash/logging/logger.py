from specdash import do_log, base_logs_directory
import datetime
import json

import traceback
import socket
from collections import OrderedDict


def get_client_ip(request):
    if 'X-Forwarded-For' in request.headers:
        client_ip = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        client_ip = request.remote_addr or 'untraceable'
    client_ip = client_ip.split(",")[::-1][0]
    return client_ip


def get_log_message_json(request, logged_metdadata):
    log = OrderedDict()

    log["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    log["host"] = socket.gethostname()

    if request is not None:
        log["client_ip"] = get_client_ip(request)
        # log["method"] = request.method
        # log["request_scheme"] = request.scheme
        # log["path"] = request.full_path

    if logged_metdadata is not None:
        for key in logged_metdadata.keys():
            log[key] = logged_metdadata[key]
        if logged_metdadata.exception is not None:
            log["exception"] = ''.join(traceback.format_exception(etype=type(logged_metdadata.exception),
                                                                  value=logged_metdadata.exception,
                                                                  tb=logged_metdadata.exception.__traceback__))

    return json.dumps(log)


class LoggedMetadata(OrderedDict):
    def __init__(self, exception=None):
        super().__init__()
        self.exception = exception


def log_message(request, logged_metadata, do_log=True):
    if do_log:
        try:
            mesasge_str = get_log_message_json(request, logged_metadata)

            now = datetime.datetime.now()
            # date_string = now.strftime('%Y-%m-%d')
            date_string = now.strftime('%Y-%m')
            if logged_metadata.exception is None:
                log_file = base_logs_directory + 'activity.log.' + date_string
            else:
                log_file = base_logs_directory + 'error.log.' + date_string

            with open(log_file, 'a', 1) as f:
                if not mesasge_str.endswith("\n"):
                    mesasge_str += "\n"
                f.write(mesasge_str)

        except Exception as e:
            error = str(e)
            # do nothing for now
