from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.locale import _


class DesignNoteAdmonition(nodes.Admonition, nodes.Element):
    pass


class DesignNoteDirective(Directive):
    has_content = True

    def run(self):
        env = self.state.document.settings.env

        target_id = "design-note-%d" % env.new_serialno("design-note")
        target_node = nodes.target("", "", ids=[target_id])

        design_note_node = DesignNoteAdmonition("\n".join(self.content))
        design_note_node += nodes.title(_("Design note"), _("Design note"))
        self.state.nested_parse(self.content, self.content_offset, design_note_node)

        return [target_node, design_note_node]


def visit_design_note(self, node):
    self.visit_admonition(node)


def depart_design_note(self, node):
    self.depart_admonition(node)


def setup(app):
    app.add_node(DesignNoteAdmonition, html=(visit_design_note, depart_design_note))
    app.add_directive("design-note", DesignNoteDirective)

    return {"version": "0.1"}
