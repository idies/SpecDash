import socket

def get_specid_list(specid_text):

    specid_text = specid_text.strip("\n")

    separators = ["\n", "|"]

    specids = []
    for sep in separators:
        if sep in specid_text:
            specids = specids + [specid.strip() for specid in specid_text.split(sep) if specid != ""]
            break
    if len(specids) == 0:
        specids = [specid_text]
    return specids


def is_server_port_used(address, port):
    # Create a TCP socket
    s = socket.socket()
    #print("Attempting to connect to %s on port %s" % (address, port))
    try:
        s.connect((address, port))
        #print("Connected to %s on port %s" % (address, port))
        return True
    except socket.error as e:
        #print("Connection to %s on port %s failed: %s" % (address, port, e))
        return False
    finally:
        s.close()

def get_unused_port(initial_port, address="127.0.0.1", max_tries=10):
    for i in range(max_tries):
        port = initial_port + i
        if not is_server_port_used(address, port):
            return port
    raise Exception("Could not find free port for Dash app (" + str(max_tries)+" tries)")