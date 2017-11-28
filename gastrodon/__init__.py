import re
from abc import ABCMeta, abstractmethod
from collections import OrderedDict, Counter
from collections import deque
from functools import lru_cache
from sys import stdout,_getframe
from types import FunctionType,LambdaType,GeneratorType,CoroutineType,FrameType,CodeType,MethodType
from types import BuiltinFunctionType,BuiltinMethodType,DynamicClassAttribute,ModuleType,AsyncGeneratorType
from typing import Dict,GenericMeta,Match
from urllib.error import HTTPError
from urllib.parse import urlparse

import pandas as pd
from IPython.display import display_png
from SPARQLWrapper import SPARQLWrapper, JSON
from pyparsing import ParseResults, ParseException
from rdflib import Graph, URIRef, Literal, BNode, RDF
from rdflib.namespace import NamespaceManager
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.plugins.sparql.processor import SPARQLResult
from rdflib.plugins.sparql.parser import parseQuery,parseUpdate

from rdflib.store import Store
from rdflib.term import Identifier, _castPythonToLiteral, Variable

#
# types that could not reasonably be expected to be serialized automatically to RDF terms in a SPARQL query.
#

_cannot_substitute={
    FunctionType,LambdaType,GeneratorType,CoroutineType,FrameType,CodeType,MethodType,
    BuiltinFunctionType,BuiltinMethodType,DynamicClassAttribute,ModuleType,AsyncGeneratorType,
    ABCMeta,GenericMeta,type
}

_pncb_regex='_A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\U00010000-\U000EFFFF'
_pncu_regex='_'+_pncb_regex
_pnc_regex='\\-0-9\u00B7\u0300-\u036F\u203F-\u2040'+_pncb_regex
_var_regex=re.compile('[?$]([%s0-9][%s0-9\u00B7\u0300-\u036F\u203F-\u2040]*)' % ((_pncu_regex,)*2))
# a modified version of the PN_LOCAL regex from the SPARQL 1.1 specification with the percentage and colon
# characters removed,  as this is used to tell if we can tell if a full URI can be safely converted to a QName
# or not
_valid_tail_regex=re.compile("[%s0-9]([%s.]*[%s])?" % (_pncu_regex,_pnc_regex,_pnc_regex))

# % (
#     PN_CHARS_U_re)

class GastrodonURI(str):
    """
        This class is used to wrap a URI that is passed from Gastrodon to Pandas and back again.  It keeps track of
        both a shortened URI (if a namespace is given) and the full URI,  so we can roundtrip this object out of the
        table and back into a SPARQL query without a chance of a short name being mistaken for an ordinary string.
    """
    def __new__(cls,short,uri_ref):
        return super().__new__(cls,short)

    def __init__(self,short,uri_ref):
        self.uri_ref=uri_ref

    def to_uri_ref(self):
        return self.uri_ref

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

_last_exception=[]

class GastrodonException(Exception):
    kwargs:Dict={}

    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        if "lines" not in kwargs:
            kwargs["lines"]=args[0].split('\n')
        self.kwargs=kwargs

    def _render_traceback_(self):
        return self.kwargs["lines"]

    @staticmethod
    def throw(*args,**kwargs):
        raise GastrodonException(*args,**kwargs) from None

class Endpoint(metaclass=ABCMeta):
    qname_regex=re.compile("(?<![A-Za-z<])([A-Za-z_][A-Za-z_0-9.-]*):")

    def __init__(self,prefixes:Graph=None,base_uri=None):
        self.prefixes=prefixes
        self.base_uri=base_uri
        if prefixes!=None:
            self._namespaces=set(map(lambda y: y if y[-1] in {"#", "/"} else y + "/", [str(x[1]) for x in prefixes.namespaces()]))

    def namespaces(self):
        prefix = [x[0] for x in self.prefixes.namespaces()]
        namespace = [x[1] for x in self.prefixes.namespaces()]
        frame = pd.DataFrame(namespace, columns=["namespace"], index=prefix)
        frame.columns.name = "prefix"
        return frame.sort_index()

    def in_namespace(self, url):
        x = str(url)
        pos = max(x.rfind('#'), x.rfind('/')) + 1
        prefix = x[:pos]
        suffix = x[pos:]
        if not _valid_tail_regex.fullmatch(suffix):
            return None

        return prefix in self._namespaces

    def ns_part(self, url):
        x = str(url)
        return x[:max(x.rfind('#'), x.rfind('/')) + 1]

    def local_part(self, url):
        x = str(url)
        return x[max(x.rfind('#'), x.rfind('/')) + 1:]

    def toPython(self,term):
        if term==None:
            return None

        if isinstance(term, URIRef):
            if self.prefixes !=None and ("/" in term.toPython() or str(term).startswith('urn:')):
                if self.base_uri and str(term).startswith(self.base_uri):
                    return GastrodonURI("<" + term[len(self.base_uri):] + ">", term)
                if self.in_namespace(term):
                    try:
                        return GastrodonURI(self.short_name(term), term)
                    except Exception:
                        pass
            return term

        return term.toPython()

    def short_name(self,term):
        prefix, namespace, name = self.prefixes.compute_qname(term)
        return ":".join((prefix, name))

    def _process_namespaces(self, sparql, parseFn):
        if self.prefixes != None:
            sparql = self.prepend_namespaces(sparql, parseFn)
        return sparql

    def _candidate_prefixes(self, sparql:str):
        return {x.group(1) for x in self.qname_regex.finditer(sparql)}

    def prepend_namespaces(self,sparql:str,parseFn):

        # extract prefixes and base uri from the query so that we won't try to
        # overwrite them

        parsed = parseFn(sparql)
        (query_base,query_ns)=_extract_decl(parsed,parseFn)

        candidates=self._candidate_prefixes(sparql)
        for (q_prefix,q_uri) in query_ns.namespaces():
            if q_prefix in candidates:
                candidates.remove(q_prefix)

        ns_section = ""
        if self.base_uri and not query_base:
            ns_section += "base <%s>\n" % (self.base_uri)

        for name,value in self.prefixes.namespaces():
            if name in candidates:
                ns_section += "prefix %s: %s\n" % (name,value.n3())

        return ns_section+sparql

    def substitute_arguments(self,sparql:str,args:Dict,prefixes:NamespaceManager) -> str:
        def substitute_one(m:Match):
            name=m.group(1)
            if name not in args:
                return m.group()
            return self.to_rdf(args[name],prefixes).n3()

        sparql = _var_regex.sub(substitute_one,sparql)
        return sparql

    def to_rdf(self, value, prefixes):
        if not isinstance(value, Identifier):
            if isinstance(value, QName):
                value = value.toURIRef(prefixes)
            elif isinstance(value, GastrodonURI):
                value = value.to_uri_ref()
            else:
                value = _toRDF(value)
        # virtuoso-specific hack for bnodes
        if isinstance(value, BNode):
            value = self.bnode_to_sparql(value)
        return value

    def bnode_to_sparql(self,bnode):
        return bnode

    def _normalize_column_type(self,column):
        if not all(filter(lambda x:x==None or type(x)==str,column)):
            return column
        try:
            return [None if x==None else int(x) for x in column]
        except ValueError:
            pass

        try:
            return [None if x==None else float(x) for x in column]
        except ValueError:
            pass

        return column


    def _dataframe(self, result:SPARQLResult)->pd.DataFrame:
        columnNames = [str(x) for x in result.vars]
        column = OrderedDict()
        for name in columnNames:
            column[name] = []
        for bindings in result.bindings:
            for variable in result.vars:
                column[str(variable)].append(self.toPython(bindings.get(variable)))

        for key in column:
            column[key] = self._normalize_column_type(column[key])

        return pd.DataFrame(column)

    def decollect(self,node):
        survey=self.select_raw("""
            SELECT ?type {
                VALUES (?type) { (rdf:Seq) (rdf:Bag) (rdf:Alt)}
                ?s a ?type
            } 
        """,bindings=dict(s=node))

        types=self._set(survey)
        if RDF.Bag in types:
            return self._decollect_Bag(node)

        return self._decollect_Seq(node)

    def _decollect_Seq(self, node):
        items=self.select_raw("""
            SELECT ?index ?item {
                ?s ?predicate ?item
                FILTER(STRSTARTS(STR(?predicate),"http://www.w3.org/1999/02/22-rdf-syntax-ns#_"))
                BIND(xsd:integer(SUBSTR(STR(?predicate),45)) AS ?index)
            } ORDER BY ?index
        """,bindings=dict(s=node))
        output=[]
        for x in items:
            output.append(self.toPython(x["item"]))
        return output


    def _decollect_Bag(self, node):
        items=self.select_raw("""
            SELECT ?item (COUNT(*) AS ?count) {
                ?s ?predicate ?item
                FILTER(STRSTARTS(STR(?predicate),"http://www.w3.org/1999/02/22-rdf-syntax-ns#_"))
                BIND(xsd:integer(SUBSTR(STR(?predicate),45)) AS ?index)
            } GROUP BY ?item 
        """,bindings=dict(s=node))
        output=Counter()

        for x in items:
            output[self.toPython(x["item"])]=self.toPython(x["count"])

        return output


    def _decollect_Seq(self, node):
        items=self.select_raw("""
            SELECT ?index ?item {
                ?s ?predicate ?item
                FILTER(STRSTARTS(STR(?predicate),"http://www.w3.org/1999/02/22-rdf-syntax-ns#_"))
                BIND(xsd:integer(SUBSTR(STR(?predicate),45)) AS ?index)
            } ORDER BY ?index
        """,bindings=dict(s=node))
        output=[]
        for x in items:
            output.append(self.toPython(x["item"]))
        return output

    def _set(self,result):
        columnNames=result.vars
        if len(columnNames)>1:
            raise ValueError("Currently can only create a set from a single column result")
        that=columnNames[0]
        output=set()
        for bindings in result.bindings:
            output.add(bindings[that])
        return output

    @abstractmethod
    def _select(self, sparql,**kwargs) -> SPARQLResult:
        pass

    @abstractmethod
    def _construct(self, sparql,**kwargs) -> Graph:
        pass

    @abstractmethod
    def _update(self, sparql,**kwargs) -> None:
        pass

    def select(self,sparql:str,**kwargs) -> pd.DataFrame:
        result = self.select_raw(sparql,_user_frame=3,**kwargs)
        frame=self._dataframe(result)
        columnNames = {str(x) for x in result.vars}
        parsed=_parseQuery(sparql)
        group_variables=_extract_group_by(parsed)

        if group_variables and all([x in columnNames for x in group_variables]):
            frame.set_index(group_variables,inplace=True)
        return frame

    def select_raw(self,sparql:str,_user_frame=2,**kwargs):
        return self._exec_raw(sparql,self._select,_user_frame,**kwargs)

    def construct(self,sparql:str,_user_frame=2,**kwargs):
        return self._exec_raw(sparql,self._construct,_user_frame,**kwargs)

    def _exec_raw(self,sparql:str,operation,_user_frame=1,**kwargs):
        try:
            sparql = self._process_namespaces(sparql, _parseQuery)
        except ParseException as x:
            lines= self._error_header()
            lines += [
                "Failure parsing SPARQL query supplied by caller;  this is either a user error",
                "or an error in a function that generated this query.  Query text follows:",
                ""
            ]
            error_lines = self._mark_query(sparql, x)
            lines += error_lines
            GastrodonException.throw("Error parsing SPARQL query",lines=lines,inner_exception=x)

        if "bindings" in kwargs:
            bindings = kwargs["bindings"]
        else:
            bindings = self._filter_frame(_getframe(_user_frame))

        sparql = self.substitute_arguments(sparql, bindings, self.prefixes)
        try:
            if "_inject_post_substitute_fault" in kwargs:
                sparql=kwargs["_inject_post_substitute_fault"]
            result = operation(sparql, **kwargs)
        except ParseException as x:
            lines= self._error_header()
            lines += [
                "Failure parsing SPARQL query after argument substitution.  This is almost certainly an error inside",
                "Gastrodon.  Substituted query text follows:",
                ""
            ]
            error_lines = self._mark_query(sparql, x)
            lines += error_lines
            GastrodonException.throw("Error parsing substituted SPARQL query",lines=lines,inner_exception=x)
        except HTTPError as x:
            lines= self._error_header()
            url_parts = urlparse(x.geturl())
            lines += [
                "HTTP Error doing Remote SPARQL query to endpoint at",
                self.url,
                ""
            ]
            lines.append(str(x))
            GastrodonException.throw("HTTP Error doing Remote SPARQL query",lines=lines,inner_exception=x)
            pass

        return result

    def _mark_query(self, sparql, x):
        error_lines = sparql.split("\n")
        error_lines.insert(x.lineno, " " * (x.col - 1) + "^")
        error_lines.append("Error at line %d and column %d" % (x.lineno, x.col))
        return error_lines

    def _error_header(self):
        return [
            "*** ERROR ***",
            "",
        ]

    def update(self,sparql:str,_user_frame=1,**kwargs) -> pd.DataFrame:
        try:
            sparql = self._process_namespaces(sparql, _parseUpdate)
        except ParseException as x:
            lines = self._error_header()
            lines += [
                "Failure parsing SPARQL update statement supplied by caller;  this is either a user error or ",
                "an error in a function that generated this query.  Query text follows:",
                ""
            ]
            error_lines = self._mark_query(sparql, x)
            lines += error_lines
            GastrodonException.throw("Error parsing SPARQL query", lines=lines, inner_exception=x)

        if "bindings" in kwargs:
            bindings = kwargs["bindings"]
        else:
            bindings=self._filter_frame(_getframe(_user_frame))
        sparql = self.substitute_arguments(sparql, bindings, self.prefixes)
        return self._update(sparql,**kwargs)

    def _filter_frame(self,that:FrameType):
        return {
            "_"+k:v for (k,v)
                in that.f_locals.items()
                if type(v) not in _cannot_substitute
                   and not k.startswith("_")
        }

class RemoteEndpoint(Endpoint):
    def __init__(self,url:str,prefixes:Graph=None,user=None,passwd=None,http_auth=None,default_graph=None,base_uri=None):
        super().__init__(prefixes,base_uri)
        self.url=url
        self.user=user
        self.passwd=passwd
        self.http_auth=http_auth
        self.default_graph=default_graph

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

    def jsonToPython(self,jsdata):
        return self.toPython(self.jsonToNode(jsdata))

    def bnode_to_sparql(self,bnode):
        return URIRef(bnode.toPython())

    def _update(self, sparql,**kwargs):
        that = self._wrapper()
        that.setQuery(sparql)
        that.setReturnFormat(JSON)
        that.setMethod("POST")
        result = that.queryAndConvert()
        return

    def _wrapper(self):
        sparql_wrapper = SPARQLWrapper(self.url)
        sparql_wrapper.user=self.user
        sparql_wrapper.passwd=self.passwd
        if self.default_graph:
            sparql_wrapper.addDefaultGraph(self.default_graph)
        if self.http_auth:
            sparql_wrapper.setHTTPAuth(self.http_auth)
        return sparql_wrapper

    def peel(self,node):
        output = self._peel(node)
        nodes=all_uri(output)
        used_ns = {URIRef(nspart(x)) for x in nodes if x.startswith('http')}
        ns_decl = [ns for ns in self.prefixes.namespaces() if ns[1] in used_ns]
        for x in ns_decl:
            output.namespace_manager.bind(*x)
        return output

    def _peel(self, node):
        output = Graph()
        query = """
            SELECT (?that as ?s) ?p ?o {
                ?that ?p ?o .
            }
        """
        items = self._select(query, bindings={"that": node})
        bnodes = set()
        q = deque()
        urins = set()
        while True:
            for x in items["results"]["bindings"]:
                s = self.jsonToNode(x["s"])
                p = self.jsonToNode(x["p"])
                o = self.jsonToNode(x["o"])
                if isinstance(s, URIRef):
                    urins.add(self.ns_part(s))
                if isinstance(p, URIRef):
                    urins.add(self.ns_part(p))
                if isinstance(p, URIRef):
                    urins.add(self.ns_part(o))

                output.add((s, p, o))
                if isinstance(o, BNode) and o not in bnodes:
                    bnodes.add(o)
                    q.append(o)

            if not q:
                return output

            # note that the detailed behavior of blank nodes tends to be different in different triple stores,
            # in particular,  although almost all triple stores have some way to refer to a blank node inside the
            # triple store,  there is no standard way to do this.
            #
            # This works with Virtuoso but I tried a number of things that don't work (such as putting a list of
            # nodeId's in the form <nodeID://b506362> in an IN clause in a FILTER statement) or things that work but
            # are too slow (filtering on STR(?s))

            items = self._select(query,bindings={"that":q.popleft()})

    def _select(self, sparql:str,**kwargs) -> SPARQLResult:
        that = self._wrapper()
        that.setQuery(sparql)
        that.setReturnFormat(JSON)
        json_result=that.queryAndConvert()
        res={}
        res["type_"] = "SELECT"
        res["vars_"] = [Variable(v) for v in json_result["head"]["vars"]]
        column = OrderedDict()
        bindings=[]
        for json_row in json_result["results"]["bindings"]:
            rdf_row={}
            for variable in res["vars_"]:
                if str(variable) in json_row:
                    rdf_row[variable]=self.jsonToNode(json_row[str(variable)])
                else:
                    rdf_row[variable]=None
            bindings.append(rdf_row)
        res["bindings"]=bindings
        return SPARQLResult(res)

    def _construct(self, sparql:str,**kwargs) -> Graph:
        result=self._select(sparql,**kwargs)
        S=Variable("s")
        P=Variable("p")
        O=Variable("o")
        neo=Graph()
        for fact in result.bindings:
            neo.add((fact[S],fact[P],fact[O]))

        return neo


class LocalEndpoint(Endpoint):
    def __init__(self,graph:Graph,prefixes:Graph=None,user=None,passwd=None,http_auth=None):
        if not prefixes:
            prefixes=graph
        super().__init__(prefixes)
        self.graph=graph

    def _select(self, sparql:str,**kwargs) -> SPARQLResult:
        return self.graph.query(sparql)

    def _construct(self, sparql:str,**kwargs) -> Graph:
        return self.graph.query(sparql)

    def _update(self, sparql:str,**kwargs) ->None :
        self.graph.update(sparql)
        return

def _toRDF(x):
    lex,datatype=_castPythonToLiteral(x)
    return Literal(lex,datatype=datatype)

def ttl(g:Store):
    s = TurtleSerializer(g)
    s.serialize(stdout,spacious=True)

def all_uri(g:Graph):
    uris = set()
    for fact in g.triples((None, None, None)):
        for node in fact:
            if isinstance(node, URIRef):
                uris.add(node)
    return uris

def nspart(uri):
    s=str(uri)
    x=max(uri.rfind('#'),uri.rfind('/'))
    return s[:x+1]


def show_image(filename):
    with open(filename, "rb") as f:
        image = f.read()
        display_png(image, raw=True)

def inline(turtle):
    g=Graph()
    g.parse(data=turtle,format="ttl")
    return LocalEndpoint(g)

def one(items):
    if isinstance(items,pd.DataFrame):
        if items.shape!=(1,1):
            raise ValueError("one(x) requires that DataFrame x have exactly one row and one column")
        return items.iloc[0,0]

    l=list(items)
    if len(l)>1:
        raise ValueError("Result has more than one member")
    if len(l)==0:
        raise IndexError("Cannot get first member from empty container")
    return l[0]

def member(index):
    return URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#_{:d}".format(index+1))

def _extract_decl(parsed: ParseResults,parseFn):
    ns=Graph()
    base_iri=None
    for decl in parsed[0] if parseFn==_parseQuery else parsed["prologue"][0]:
        if 'prefix' in decl:
            ns.bind(decl["prefix"],decl["iri"],override=True)
        elif 'iri' in decl:
            base_iri=decl["iri"]
    return (base_iri,ns)

@lru_cache()
def _parseUpdate(sparql):
    return parseUpdate(sparql)

@lru_cache()
def _parseQuery(sparql):
    return parseQuery(sparql)

def _extract_group_by(parsed):
    main_part=parsed[1]
    if 'groupby' not in main_part:
        return []

    if not all([type(x)==Variable for x in main_part['groupby']['condition']]):
        return []

    return [str(x) for x in main_part['groupby']['condition']]

