from setuptools import setup, find_packages

setup(name='specdash',
      version='0.1.0',
      description='Visualization and analysis tool for 1-dimensional astronomical spectra.',
      url='http://github.com/mtaghiza/specdash',
      author='Manuchehr Taghizadeh-Popp',
      author_email='mtaghiza@jhu.edu',
      license='Apache 2.0',
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      package_data={"specdash": ['assets/*']}
      )
