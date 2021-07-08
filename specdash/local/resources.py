import pkg_resources
from .. import package_name


def get_text_lines(relative_file_path):
    file = pkg_resources.resource_stream(package_name, relative_file_path)
    try:
        line_list = file.readlines()
    except:
        try:
            file.close()
        except:
            pass
    return line_list
