from setuptools import setup, find_packages

setup(name='specdash',
      version='0.2.0',
      description='Visualization and analysis tool for 1-dimensional astronomical spectra.',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      keywords='astronomy analysis-pipeline spectroscopy',
      url='http://github.com/idies/specdash',
      author='Manuchehr Taghizadeh-Popp',
      author_email='mtaghiza@jhu.edu',
      license='Apache 2.0',
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      package_data={"specdash": ['assets/*']}
      )
