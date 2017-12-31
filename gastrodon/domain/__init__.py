from sphinxcontrib.domaintools import custom_domain
import re

from docutils import nodes
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.domains.std import GenericObject
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

import pydevd
pydevd.settrace('localhost', port=10212, stdoutToServer=True, stderrToServer=True)

#
# TODO: URI reference appears in box like other references
#

class URIRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        return (title,target)

class Subject(ObjectDescription):
    def handle_signature(self, sig, signode):
        signode += addnodes.desc_name(sig,sig)
        return sig

    domain = "rdf"

    def add_target_and_index(self, name, sig, signode):
        super().add_target_and_index(name, sig, signode)
        targetname = '%s-%s' % (self.objtype, name)
        signode['ids'].append(targetname)
        self.state.document.note_explicit_target(signode)
        self.env.domaindata[self.domain]['objects'][name] = \
            self.env.docname, targetname

    indextemplate = l_('RDF Subject; %s')


class RDFDomain(Domain):
    name = 'rdf'
    label = 'RDF'

    object_types={
        'uri':ObjType('uri','uri')
    }

    roles = {
        'uri':  URIRefRole(),
    }

    directives = {
        'uri':Subject
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

def setup(app):
    print("Adding the RDFDomain")
    app.add_domain(RDFDomain)