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

The architecture of domains in Sphinx is a bit weaker than I wish it was.  My basic complaint is
that the Python domain is one set of directives tangled up in the Python domain API.  Then there
is a set of :rst:dir:`autodoc` and :rst:dir:`autosummary` related directives that implement automatic operations on
the python domain that sit separately in different extensions.

There is

https://bitbucket.org/klorenz/sphinxcontrib-domaintools

which is makes it possible to define domains with a declarative syntax,  this is a huge
improvement,  but that doesn't come with an "autodoc" replacement or an obvious way to bolt one
on.

To be truely universal it is tempting to introduce an  `rdf` or `uri` domain which points to a
named RDF resource (no blank nodes?)  I don't know how parsing of colons and other
meaningful characters would work,  but replicating RDF namespace mechanism would be great.

An alternative strategy could be to  introduce an `rdfs` or `owl` or `bibo` domain which represents
a particular RDF namespace.

We like :class:`gastrodon.Endpoint` don't we?

Let's work out how subjects such be parsed.  In an :rst:directive:`rdf:subject` the possible inputs are either

#. A full URI written as an RDF termlike '<http://www.w3.org/2000/01/rdf-schema#Class>'
#. A full URI written as a string 'http://www.w3.org/2000/01/rdf-schema#'
#. A qname,  ex, `rdfs:Class`

That's the input.  The output depends on what we are using it for.  Now the visible output should be a qname if possible
(matching namespace declaration) or otherwise should be the full URI.  Internally,  however,  the name at which it
is indexed on should be canonical.

The same is true for URI references as roles.

It may be better to support 'psuedo-qnames` that have characters that would not be allowed in a qname.  This would be
helpful while referring to Dbpedia and similar subjects but might confuse people who use other tools.

.. rdf:subject:: rdfs:Class

	i hope next year is better than last year, very much, thank you please...
