import pkg_resources
import json

from .local.resources import get_text_lines

#http://classic.sdss.org/dr6/algorithms/linestable.html
#https://classic.sdss.org/dr7/algorithms/speclinefits.html

#https://iopscience.iop.org/article/10.1086/132961/pdf
#https://iopscience.iop.org/article/10.1086/316552/pdf
#http://adsabs.harvard.edu/pdf/2004JKAS...37...87S
#http://tdc-www.harvard.edu/iraf/rvsao/emsao/ex2/emsao.sky.lines.html
#http://skinakas.physics.uoc.gr/en/images/weather_data/SkinakasSkyBrghtSpectroscopy.pdf
#https://github.com/iraf-community/iraf/blob/master/noao/lib/linelists/skylines.dat

def get_spectral_lines_from_json():
    package_name = __name__  # Could be any module/package name
    resource_path = 'assets/spectral_lines.json'  # Do not use os.path.join()
    spectrum_lines_file = pkg_resources.resource_stream(package_name, resource_path)
    content_dict = json.loads(spectrum_lines_file.read())
    spectrum_lines_file.close()
    return content_dict


def get_spectral_lines():

    lineList = get_text_lines('assets/spectral_lines.txt')
    spectral_lines = {}
    for item in lineList:
        listTemp = item.split()
        listTemp = [ item.decode('ascii') for item in listTemp]
        # print(listTemp)
        spectral_line = {}
        id = listTemp[1] + " " + listTemp[0]
        spectral_line["fullname"] = id
        spectral_line["lambda"] = float(listTemp[0])
        spectral_line["name"] = listTemp[1]
        spectral_line["label"] = listTemp[2]
        spectral_lines[id] = spectral_line

    return spectral_lines


def get_sky_lines():


    line_list = get_text_lines('assets/sky_lines.txt')
    sky_lines = {}
    for item in line_list:
        listTemp = item.split()
        listTemp = [ item.decode('ascii') for item in listTemp]
        # print(listTemp)
        sky_line = {}
        id = listTemp[1] + " " + listTemp[0]
        sky_line["fullname"] = id
        sky_line["lambda"] = float(listTemp[0])
        sky_line["name"] = listTemp[1]
        sky_line["label"] = listTemp[2]
        sky_lines[id] = sky_line

    return sky_lines


def get_artificial_lines():


    line_list = get_text_lines('assets/artificial_lines.txt')
    artificial_lines = {}
    for item in line_list:
        listTemp = item.split()
        listTemp = [ item.decode('ascii') for item in listTemp]
        # print(listTemp)
        line = {}
        id = listTemp[1] + " " + listTemp[0]
        line["fullname"] = id
        line["lambda"] = float(listTemp[0])
        line["name"] = listTemp[1]
        line["label"] = listTemp[2]
        artificial_lines[id] = line

    return artificial_lines


spectral_lines = get_spectral_lines()
sky_lines = get_sky_lines()
artificial_lines = get_artificial_lines()