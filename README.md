# SpecDash

SpecDash is an application for displaying and analyzing one-dimensional astronomical spectra, available both as an interactive or programmable Jupyter notebook widget, as well as a stand-alone website. 

Users can load and compare multiple spectra at the same time, overlay error bars, spectral masks and lines, and show individual exposure frames, sky background and model spectra.
For modeling, spectral regions can be interactively selected for fitting the continuum or spectral lines with several predefined models, and spectral smoothing can be performed with with several kernels.
For reproducibility, all spectra and models can be downloaded, shared, and then uploaded again by other users.

Author: Manuchehr Taghizadeh-Popp, Johns Hopkins University. Email: mtaghiza@jhu.edu

License: `Apache 2.0`

Citation: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5083750.svg)](https://doi.org/10.5281/zenodo.5083750)

Web interface: http://specdash.idies.jhu.edu/

API Documentation: http://specdash.idies.jhu.edu/static/docs/index.html

### Installation:  

- Install dependencies:  
``pip install -r requirements.txt``


- Install SpecDash:  
``pip install .``


- If required package jupyter-dash was installed for the first time, then JupyterLab might need to be rebuilt:  
 ``jupyter lab build``   (this requires nodejs: ``conda install nodejs``)
