API Documentation
******************

Endpoints
=========

.. module:: gastrodon

.. autoclass:: Endpoint

   **Core Methods**

   The `select`, `construct`, and `update` methods are the ones that you will use most often.  All of these do
   SPARQL queries or SPARQL updates on the RDF Graph fronted by this Endpoint.   If the endpoint is large or
   remote,  these functions could consume an unlimited time.

   .. automethod:: select
   .. automethod:: construct
   .. automethod:: update

   **Graph Conversion Methods**

   Methods in this category convert between complex RDF structures inside the endpoint (eg. RDF Collections, a
   document record containing blank nodes) to Python data structures outside the endpoint (such Lists,  Sets,
   Bags, Counters, Trees, and even rdflib Graphs)

   .. automethod:: decollect

   **Local Methods**

   These methods run quickly because they do not depend on the fronted RDF Graph; these are appropriate to use by callers such as `apply`
   methods and variants used in Pandas and similar software.

   .. automethod:: toPython
   .. automethod:: namespaces
   .. automethod:: ns_part
   .. automethod:: local_part
   .. automethod:: short_name
   .. automethod:: in_namespace


Endpoint Implementations
========================

.. autoclass:: LocalEndpoint
   :members:

.. autoclass:: RemoteEndpoint
   :members:

Supporting Classes and Functions
================================

.. autoclass:: QName
   :members:

.. autofunction:: inline
.. autofunction:: ttl
.. autofunction:: one
.. autofunction:: member
.. autofunction:: all_uri
.. autofunction:: show_image

Objects Created Only By Gastrodon
=================================

.. autoclass:: GastrodonURI
   :members:

.. autoclass:: GastrodonException
   :members:



