URI Resolution Examples
=======================

Probably the best way to explain URI resolution in roles and directives is to work through some examples. The
work is done internally with a :class:`gastrodon.domain.UriResolver`,  which takes both a set of namespace
declarations and a base URI.

.. testsetup:: *

   from gastrodon.domain import UriResolver

.. doctest::

	>>> x=UriResolver(
	... 	{
	...     	"rdfs":"http://www.w3.org/2000/01/rdf-schema#",
	...         "dc":"http://purl.org/dc/elements/1.1/"
	...		},
	...		"http://dbpedia.org/resource/")

Writing URIs in Sphinx Markup
-----------------------------

In either a directive or a role,  the target or signature is processed to a URI string for indexing,
so that no matter how a URI is written,  the URI will be matched inside Sphinx.  Plain URIs can be written
with or without the angle brackets that one would use to write them in Turtle.  URIs are resolved relative
to the base URI in case a URI is not complete.

.. doctest::

	>>> x.any_to_uri("Curry")
	'http://dbpedia.org/resource/Curry'
	>>> x.any_to_uri("<Proton>")
	'http://dbpedia.org/resource/Proton'
	>>> x.any_to_uri("<..>")
	'http://dbpedia.org/'
	>>> x.any_to_uri("/ontology/Person")
	'http://dbpedia.org/ontology/Person'
	>>> x.any_to_uri("http://slashdot.org/")
	'http://slashdot.org/'
	>>> x.any_to_uri("<http://reddit.com/>")
	'http://reddit.com/'

It is also possible to write URIs as *Qualified Names* (QNames) or at least an close approximation.  If a
URI does not contain angle brackets,  and begins with a declared prefix,  it is resolved relative to that
namespace.

.. doctest::

	>>> x.any_to_uri("rdfs:Class")
	'http://www.w3.org/2000/01/rdf-schema#Class'
	>>> x.any_to_uri("dc:title")
	'http://purl.org/dc/elements/1.1/title'

The difference between this convention and QNames is that,  in Sphinx markup,  you can use an unlimited range
of characters after the prefix,  whereas the legacy of XML means that QNames don't allow constructions like

.. doctest::

	>>> x.any_to_uri("dc:Work/title")
	'http://purl.org/dc/elements/1.1/Work/title'

(This is not a real predicate from the Dublin Core vocabulary,  but this is useful while documenting
certain vocabularies,  such as DBpedia,  where you will find slashes,  parenthesis and other unusual
characters in the URIs.)

How URIs are displayed in Sphinx Markup
---------------------------------------

When displaying titles for roles and directives,  Sphinx markup is processed through the
:method:gastrodon.domain.UriResolver.humanize_uri` method,  which displays URIs in a human-friendly
manner.  Note that short URIs might contain characters that are not valid in QNames.


.. doctest::

	>>> x.humanize_uri("http://www.w3.org/2000/01/rdf-schema#Class")
	'rdfs:Class'
	>>> x.humanize_uri("http://purl.org/dc/elements/1.1/title")
	'dc:title'
	>>> x.humanize_uri("https://tonyortega.org/")
	'<https://tonyortega.org/>'
	>>> x.humanize_uri("http://dbpedia.org/resource/Fishbone")
	'<Fishbone>'