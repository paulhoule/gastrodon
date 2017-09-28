Example notebooks are divided into groups.

[local](local): Local notebooks use only the resources on the host machine.  If they do SPARQL queries,  they use the rdflib graph
object,  working entirely within memory.  Local notebooks can be used to implement unit tests but they will run quickly and reliabily.

[remote](remote): Remote notebooks access remote resources such as SPARQL protocol endpoints.  (ex. <a href="http://dbpedia.org/sparql">The DBpedia Public SPARQL endpoint</a>)
The performance and availability of remote resources can vary,  however,  so these notebooks are not appropriate for unit testing 
