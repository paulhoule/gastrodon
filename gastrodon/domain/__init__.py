import re
from string import ascii_lowercase
from urllib.parse import urljoin

from docutils.frontend import Values, OptionParser
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.states import Inliner
from docutils.utils import new_reporter, new_document
from rdflib import Graph

from docutils import nodes, frontend
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.domains.std import GenericObject
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription, nl_escape_re, strip_backslash_re
from sphinx.roles import XRefRole
from sphinx.util.docfields import DocFieldTransformer
from sphinx.util.nodes import make_refnode
from docutils.nodes import Text, document


class URIRefRole(XRefRole):
    domain="rdf"

    def process_link(self, env, refnode, has_explicit_title, title, target):
        resolver=env.domaindata[self.domain]["resolver"]
        target=resolver.any_to_uri(target)
        if not has_explicit_title:
            title=resolver.humanize_uri(target)
        return (title,target)

class FlexibleObjectDescription(ObjectDescription):
    def run(self):
        # type: () -> List[nodes.Node]
        """
        Main directive entry function, called by docutils upon encountering the
        directive.

        This directive is meant to be quite easily subclassable, so it delegates
        to several additional methods.  What it does:

        * find out if called as a domain-specific directive, set self.domain
        * create a `desc` node to fit all description inside
        * parse standard options, currently `noindex`
        * create an index node if needed as self.indexnode
        * parse all given signatures (as returned by self.get_signatures())
          using self.handle_signature(), which should either return a name
          or raise ValueError
        * add index entries using self.add_target_and_index()
        * parse the content and handle doc fields in it
        """
        node = self.configure_node()
        self.process_signature(node)
        self.process_content(node)
        return [self.indexnode, node]

    def configure_node(self):
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name
        self.env = self.state.document.settings.env  # type: BuildEnvironment
        self.indexnode = addnodes.index(entries=[])
        node = addnodes.desc()
        node.document = self.state.document
        node['domain'] = self.domain
        # 'desctype' is a backwards compatible attribute
        node['objtype'] = node['desctype'] = self.objtype
        node['noindex'] = ('noindex' in self.options)
        return node

    def process_content(self, node):
        contentnode = addnodes.desc_content()
        node.append(contentnode)
        if self.names:
            # needed for association of version{added,changed} directives
            self.env.temp_data['object'] = self.names[0]
        self.before_content()
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        self.transform_content(contentnode)
        self.env.temp_data['object'] = None
        self.after_content()

    def transform_content(self, contentnode):
        DocFieldTransformer(self).transform_all(contentnode)

    def process_signature(self, node):
        self.names = []  # type: List[unicode]
        signatures = self.get_signatures()
        for i, sig in enumerate(signatures):
            # add a signature node for each signature in the current unit
            # and add a reference target for it
            signode = addnodes.desc_signature(sig, '')
            signode['first'] = False
            node.append(signode)
            try:
                # name can also be a tuple, e.g. (classname, objname);
                # this is strictly domain-specific (i.e. no assumptions may
                # be made in this base class)
                name = self.handle_signature(sig, signode)
            except ValueError:
                # signature parsing failed
                signode.clear()
                signode += addnodes.desc_name(sig, sig)
                continue  # we don't want an index entry here
            if name not in self.names:
                self.names.append(name)
                if not node["noindex"]:
                    # only add target and index entry if this is the first
                    # description of the object with this name in this desc block
                    self.add_target_and_index(name, sig, signode)

class RDFFieldTransformer:
    def __init__(self,owner):
        self.env=owner.env
        self.domain=owner.domain

    def transform_all(self, node):
        # type: (nodes.Node) -> None
        """Transform all field list children of a node."""
        # don't traverse, only handle field lists that are immediate children
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self,node):
        for field in node.children:
            field_name=field.children[0]

            str_name=str(field_name.children[0])
            if " " in str_name:
                parts=str_name.split(" ")
                if len(parts)==2:
                    field_name.clear()
                    for subnode in self.create_role(str_name,str_name.replace(" ",":")):
                        field_name += subnode
                    continue


            field_name+=Text(str_name)

        return node

    def create_role(self,rawtext,text):
        uriRole=self.env.domains["rdf"].roles["uri"]
        fake_inliner=Inliner()
        settings=frontend.OptionParser().get_default_values()
        settings._update_loose({"env":self.env})
        fake_inliner.document=new_document("Field Name: "+rawtext,settings)
        fake_inliner.reporter=fake_inliner.document.reporter
        def get_source_and_line(lineno=None):
            # type: (int) -> Tuple[unicode, int]
            return "Field Name: "+rawtext, None

        fake_inliner.reporter.get_source_and_line = get_source_and_line
        return uriRole("rdf:uri",rawtext,text,None,fake_inliner)


class Subject(FlexibleObjectDescription):
    def get_signatures(self):
        # type: () -> List[unicode]
        """
        Retrieve the signatures to document from the directive arguments.  By
        default, signatures are given as arguments, one per line.

        Backslash-escaping of newlines is supported.
        """
        lines = nl_escape_re.sub('', self.arguments[0]).split('\n')
        return [strip_backslash_re.sub(r'\1', line.strip()) for line in lines]

    def handle_signature(self, sig, signode):
        resolver=self.env.domaindata[self.domain]["resolver"]
        sig=resolver.any_to_uri(sig)
        signode += addnodes.desc_name(sig, resolver.humanize_uri(sig))
        return sig

    def add_target_and_index(self, name, sig, signode):
        tbox=self.env.config.rdf_tbox
        nsmgr=tbox.namespace_manager
        targetname = squash_uri_to_label('%s-%s' % (self.objtype, name))
        signode['ids'].append(targetname)
        self.state.document.note_explicit_target(signode)
        self.env.domaindata[self.domain]['objects'][name] = \
            self.env.docname, targetname

    def transform_content(self, contentnode):
        RDFFieldTransformer(self).transform_all(contentnode)

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
