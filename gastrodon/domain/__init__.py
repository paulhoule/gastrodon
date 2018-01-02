import re
from string import ascii_lowercase
from urllib.parse import urljoin

from rdflib import Graph

from docutils import nodes
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.domains.std import GenericObject
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

#import pydevd
#pydevd.settrace('localhost', port=10212, stdoutToServer=True, stderrToServer=True)

class URIRefRole(XRefRole):
    domain="rdf"
    def process_link(self, env, refnode, has_explicit_title, title, target):
        resolver=env.domaindata[self.domain]["resolver"]
        target=resolver.any_to_uri(target)
        if not has_explicit_title:
            title=resolver.humanize_uri(target)
        return (title,target)

class Subject(ObjectDescription):
    def handle_signature(self, sig, signode):
        resolver=self.env.domaindata[self.domain]["resolver"]
        sig=resolver.any_to_uri(sig)
        signode += addnodes.desc_name(sig, resolver.humanize_uri(sig))
        return sig

    domain = "rdf"

    def add_target_and_index(self, name, sig, signode):

        tbox=self.env.config.rdf_tbox
        nsmgr=tbox.namespace_manager
        targetname = squash_uri_to_label('%s-%s' % (self.objtype, name))
        signode['ids'].append(targetname)
        self.state.document.note_explicit_target(signode)
        self.env.domaindata[self.domain]['objects'][name] = \
            self.env.docname, targetname

    indextemplate = l_('RDF Subject; %s')


class RDFDomain(Domain):
    def __init__(self, env):
        super().__init__(env)
        ns_source=env.config.rdf_tbox.namespaces()
        ns={t[0]:str(t[1]) for t in ns_source}
        self.env.domaindata[self.name]["resolver"]=UriResolver(ns,"http://rdf.ontology2.com/scratch/")

    name = 'rdf'
    label = 'RDF'

    object_types={
        'uri':ObjType('uri','uri')
    }

    roles = {
        'uri':  URIRefRole(),
    }

    directives = {
        'subject':Subject
    }

    initial_data = {
        'objects': {}
    }

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        if target in self.data['objects']:
            docname, labelid = self.data['objects'][target]
        else:
            docname, labelid = '', ''
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

def squash_uri_to_label(name):
    output=[]
    for c in name:
        l=c.lower()
        if l.isnumeric() or l in ascii_lowercase or l=="-" or l=="_":
            output += [l]
        else:
            output += ["-"]
    return "".join(output)

class UriResolver:
    namespaces : dict
    base_uri : str

    def __init__(self,namespaces,base_uri):
        self.namespaces=namespaces
        self.base_uri=base_uri


    def any_to_uri(self,text):
        if text.startswith("<") and text.endswith(">"):
            return urljoin(self.base_uri,text[1:-1])

        parts=text.split(":",1)
        if len(parts)==1:
            return urljoin(self.base_uri,parts[0])

        if parts[0] in self.namespaces:
            return self.namespaces[parts[0]]+parts[1]

        return text

    def humanize_uri(self,uri):
        if uri.startswith(self.base_uri):
            return "<"+uri[len(self.base_uri):]+">"

        for (prefix,ns) in self.namespaces.items():
            if uri.startswith(ns):
                return prefix+':'+uri[len(ns):]

        return "<"+uri+">"

def setup(app):
    print("Adding the RDFDomain")
    app.add_config_value("rdf_tbox",Graph(),'env')
    app.add_domain(RDFDomain)
