from typing import Dict

from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, URIRef, Literal, BNode, RDF
from rdflib.store import Store
from rdflib.term import Identifier,_castPythonToLiteral
from rdflib.namespace import NamespaceManager
from rdflib.plugins.serializers.turtle import TurtleSerializer
from sys import stdout
from collections import deque

from collections import OrderedDict
import pandas as pd

class QName:
    def __init__(self,name:str):
        self.name=name

    def toURIRef(self,manager:NamespaceManager) -> URIRef:
        if ":" not in self.name:
            return None

        head,tail=self.name.split(':',1)
        for prefix,ns in manager.namespaces():
            if prefix==head:
                return ns+tail
        return URIRef(self.name)


class Endpoint:
    def __init__(self,url:str,prefixes:Graph=None):
        self.url=url
        self.prefixes=prefixes
        if prefixes!=None:
            self.namespaces=set(map(lambda y: y if y[-1] in {"#","/"} else y+"/",[str(x[1]) for x in prefixes.namespaces()]))

    def in_namespace(self,url):
        x=str(url)
        ns=x[:max(x.rfind('#'),x.rfind('/'))+1]
        return ns in self.namespaces

    def ns_part(self,url):
        x=str(url)
        return x[:max(x.rfind('#'),x.rfind('/'))+1]

    def jsonToNode(self,jsdata):
        type = jsdata["type"]
        value = jsdata["value"]
        if type == "uri":
            return URIRef(value)
        if type == "typed-literal":
            return Literal(value, datatype=jsdata["datatype"])
        if type == "literal":
            return Literal(value)
        if type == "bnode":
            return BNode(value)
        return None

    def toPython(self,term):
        if isinstance(term, URIRef):
            if self.prefixes !=None and "/" in term.toPython() and self.in_namespace(term):
                return self.prefixes.qname(term)
        return term.toPython()

    def jsonToPython(self,jsdata):
        return self.toPython(self.jsonToNode(jsdata))

    def select(self,sparql:str,**kwargs) -> pd.DataFrame:
        result = self._select(sparql,**kwargs)
        return self._dataframe(result)

    def _dataframe(self, result):
        columnNames = result["head"]["vars"]
        column = OrderedDict()
        for name in columnNames:
            column[name] = []
        for bindings in result["results"]["bindings"]:
            for name in bindings:
                column[name].append(self.jsonToPython(bindings[name]))
        return pd.DataFrame(column)

    def _set(self,result,node_function=None):
        if node_function==None:
            node_function=self.jsonToPython

        columnNames=result["head"]["vars"]
        if len(columnNames)>1:
            raise ValueError("Currently can only create a set from a single column result")
        that=columnNames[0]
        output=set()
        for bindings in result["results"]["bindings"]:
            output.add(node_function(bindings[that]))
        return output

    def _select(self, sparql:str,**kwargs) -> dict:
        that = SPARQLWrapper(self.url)
        if self.prefixes != None:
            sparql = self.prepend_namespaces(sparql)
        sparql = self.substitute_arguments(sparql, kwargs, self.prefixes)
        that.setQuery(sparql)
        that.setReturnFormat(JSON)
        result=that.queryAndConvert()
        return result


    def substitute_arguments(self,sparql:str,args:Dict,prefixes:NamespaceManager) -> str:
        for name,value in args.items():
            if not isinstance(value,Identifier):
                if isinstance(value,QName):
                    value=value.toURIRef(prefixes)
                else:
                    value=_toRDF(value)
            # virtuoso-specific hack for bnodes
            if isinstance(value,BNode):
                value=URIRef(value.toPython())
            sparql=sparql.replace("?"+name,value.n3())
        return sparql

    def prepend_namespaces(self,sparql:str):
        ns_section=""
        for name,value in self.prefixes.namespaces():
            ns_section += "prefix %s: %s\n" % (name,value.n3())

        return ns_section+sparql

    def unpack(self,node,node_function=None):
        node_function=self.default_node_function(node_function)
        survey=self._select("""
            SELECT ?type {
                ?s a ?type
            } 
        """,s=node)

        types=self._set(survey,node_function=self.jsonToNode)
        if RDF.Seq in types:
            return self._unpack_Seq(node,node_function)

    def _unpack_Seq(self, node,node_function=None):
        node_function=self.default_node_function(node_function)
        items=self._select("""
            SELECT ?index ?item {
                ?s ?predicate ?item
                FILTER(STRSTARTS(STR(?predicate),"http://www.w3.org/1999/02/22-rdf-syntax-ns#_"))
                BIND(xsd:integer(SUBSTR(STR(?predicate),45)) AS ?index)
            } ORDER BY ?item
        """,s=node)
        output=[]
        for x in items["results"]["bindings"]:
            output.append(node_function(x["item"]))
        return output


    def peel(self,node):
        output=Graph()
        items=self._select("""
            SELECT ?s ?p ?o {
                ?s ?p ?o .
                FILTER (?s=?that)
            } 
        """,that=node)
        bnodes=set()
        q=deque()
        urins=set()

        while True:
            for x in items["results"]["bindings"]:
                s=self.jsonToNode(x["s"])
                p=self.jsonToNode(x["p"])
                o=self.jsonToNode(x["o"])
                if isinstance(s,URIRef):
                    urins.add(self.ns_part(s))
                if isinstance(p,URIRef):
                    urins.add(self.ns_part(p))
                if isinstance(p,URIRef):
                    urins.add(self.ns_part(o))

                output.add((s,p,o))
                if isinstance(o,BNode) and o not in bnodes:
                    bnodes.add(o)
                    q.append(o)

            if not q:
                print(urins)
                return output

            stick=[]
            while q:
                stick.append("(<%s>)" % (str(q.popleft())))
                if(len(stick))>10:
                    break
            # note that the detailed behavior of blank nodes tends to be different in different triple stores,
            # in particular,  although almost all triple stores have some way to refer to a blank node inside the
            # triple store,  there is no standard way to do this.
            #
            # This works with Virtuoso but I tried a number of things that don't work (such as putting a list of
            # nodeId's in the form <nodeID://b506362> in an IN clause in a FILTER statement) or things that work but
            # are too slow (filtering on STR(?s))

            query = """
                SELECT ?s ?p ?o {
                    VALUES (?s) {%s}
                    ?s ?p ?o .
                }
            """ % " ".join(stick)
            items=self._select(query)

    def default_node_function(self,that):
        if that==None:
            return self.jsonToPython
        return that


def _toRDF(x):
    lex,datatype=_castPythonToLiteral(x)
    return Literal(lex,datatype=datatype)

def ttl(g:Store):
    s = TurtleSerializer(g)
    s.serialize(stdout)

#
# TODO: convert RDF Collections/Lists to and from RDF lists!
# TODO: RDF to and from Python dict/list/scalar (a lot like JSON-LD!)
# TODO: Cut out an XMP packet out of the whole!
#
