Sphinx Metaobjects
==================

How do we do it?

:rdf:uri:`http://www.w3.org/2000/01/rdf-schema#Class`

In the abstract,  Sphinx has an appealing capability of modelling multiple "domains"
simultaneously.  This way we could write about a set of Python definitions (of modules,
methods,  etc.) and also C definitions for associated code in the same project.

What would really be cool is to apply the same facilities to both code and model objects:
thus the REST API definition written in a language like RAML,  with the Python code object.
Similarly I want to visualize OWL and RDF ontologies.

Some Use Cases
--------------

* Document an RDFS Ontology
* Document an OWL Ontology
* Document some domain described by an RDFS or OWL ontology (instances of the classes defined in the model)
* Document an set of EMOF definitions

Thoughts on Architecture
------------------------

There is not a lot of shared code between Sphinx domains;  each domain has its own unique way of doing
things (can be customized),  but the implementation of a new domain is tedious.  If you want automatic
extraction of markup (eg. the :module:`sphinx.ext.autodoc`) extension that has to be done fresh for
each language you support.  If you want to render summaries (eg. the :module:`sphinx.ext.autosummary`)
that is also domain dependent.

The following package

https://bitbucket.org/klorenz/sphinxcontrib-domaintools

helps you create domains with model-based definitions,  but it doesn't do anything in the extraction
or summary departments.  Rather than building on that,  I decided to build a minimalist framework
for RDF and layer features on top of it.  `sphinxcontrib-domaintools` does point out how dynamic we
can get.  Based on data we have at initialization time (all or part of the RDF graph),  we can
create new roles and directives.  We could also create multiple instances of the RDF domain with
different graphs and configurations.

The Core vocabulary
-------------------

.. rst:role:: rdf:uri

	The uri role.  Use this role to refer to a named URI resource.  The following formats are supported::

		:rdf:uri:`rdfs:Class`
		:rdf:uri:`http://www.w3.org/2000/01/rdf-schema#Class`
		:rdf:uri:`<http://www.w3.org/2000/01/rdf-schema#Class>`

	see :doc:`uri_resolution_examples` for details.  If a namespace is declared,  uris in that namespace
	will be displayed in shortened form (eg. :rdf:uri:`rdfs:Class`) but will otherwise be displayed in long form
	(eg. :rdf:uri:`http://example.com/`)

.. rst:directive:: rdf:subject

	The `rdf:subject` directive contains a description of a named URI resource.  You can think of this
	as a description of the URI,  or as a description of the thing the URI refers to.  Here is an example::

		.. rdf:subject:: rdfs:Class



			:rdfs isDefinedBy: :rdf:uri:`http://www.w3.org/2000/01/rdf-schema#`
			:rdfs label: Class
			:rdfs comment: The class of classes.
			:rdfs subClassOf: :rdf:uri:`rdfs:Resource`

	which renders like

	.. rdf:subject:: rdfs:Class

		This is what I have to say about this wooly and wonderful subject!

		:rdfs isDefinedBy: :rdf:uri:`http://www.w3.org/2000/01/rdf-schema#`
		:rdfs label: - Class
		:rdfs comment: The class of classes.
		:rdfs subClassOf: :rdf:uri:`rdfs:Resource`

	Triples are represented using the `Field List`_ mechanism in reStructuredText.  Because colons are not
	allowed in field names without escaping,  the prefix is separated from the localname with a space.

.. _Field List: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#field-lists
