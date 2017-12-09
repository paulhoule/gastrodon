.. gastrodon documentation master file, created by
   sphinx-quickstart on Wed Dec  6 12:38:20 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to gastrodon's documentation!
=====================================

Release |release|

About Gastrodon
---------------

Gastrodon links databases that support the SPARQL protocol (`more than
ten! <https://www.w3.org/wiki/LargeTripleStores>`__) to
Pandas, a popular Python library for
analysis of tabular data. Pandas, in turn, is connected to a vast number
of visualization, statistics, and machine learning tools, all of which
work with `Jupyter <https://jupyter.org/>`__ notebooks. The result is an
ideal environment for telling stories that reveal the value of data,
ontologies, taxonomies, and models.

In addition to remote databases, Gastrodon can do SPARQL queries over
in-memory RDF graphs (from
`rdflib <https://github.com/RDFLib/rdflib>`__). It has facilities to
copy subgraphs from one graph to another, making it possible to assemble
local graphs that contain facts relevant to a particular decision, work
on them intimately, and then store results in a permanent triple store.

Learning to use Gastrodon
-------------------------

This manual contains detailed API documentation for Gastrodon.  For
examples of Jupyter notebooks that use Gastrodon,  see the
`Example notebooks <https://github.com/paulhoule/gastrodon/tree/master/notebooks>`__.

The following reference documentation should be helpful:

-  `Pandas <http://pandas.pydata.org/pandas-docs/stable/>`__
-  `Jupyter <http://jupyter.org/index.html>`__
-  `rdflib <https://github.com/RDFLib/rdflib#readme>`__
-  `SPARQL <http://www.w3.org/TR/2013/REC-sparql11-query-20130321/#basicpatterns>`__

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents:

   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
