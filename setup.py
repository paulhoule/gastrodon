"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='gastrodon',
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    description='Toolkit to display,  analyze,  and visualize data and documents based on RDF graphs and the SPARQL query language using Pandas,  Jupyter, and other Python ecosystem tools.',
    long_description=long_description,
    url='https://github.com/paulhoule/gastrodon',
    author='Paul Houle',
    author_email='paul.houle@ontology2.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
        'Topic :: Database :: Front-Ends',
        'Topic :: Documentation :: Sphinx',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],

    # What does your project relate to?
    keywords='sparql rdf rdflib pandas visualization',
    packages=find_packages(exclude=['art','notebooks']),
    install_requires=['rdflib','pyparsing','IPython','SPARQLWrapper','uritools','pandas','ipython-autotime','matplotlib','bs4'],
)