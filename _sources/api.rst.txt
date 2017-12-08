API Reference
*************

This reference is organized to put the most important information first,  both overall and within each section.  You
will mainly be working with implementations of the `Endpoint` object such as `LocalEndpoint` and `RemoteEndpoint`


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

   .. automethod:: to_python
   .. automethod:: namespaces
   .. automethod:: ns_part
   .. automethod:: local_part
   .. automethod:: short_name
   .. automethod:: is_ok_qname


Endpoint Implementations
========================

If you wish to use an `Endpoint` you must instantiate one of the following implementations.

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

You probably could (and should) get by without knowing about these two objects.  Both of these are created by
Gastrodon to play particular roles in the IPython and Pandas environment.

.. autoclass:: GastrodonURI
   :members:
.. autoclass:: GastrodonException
   :members:



