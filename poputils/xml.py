"""
Various utilitites for working with XML and the lxml library.
"""


import re

from lxml import etree


def format_document(doc, linewidth=72):
    """
    Formats a an XML document using the lxml pretty print function and
    indenting attributes for long lines.

    The ``doc`` parameter has to be an lxml.etree.ElementTree object.
    """

    def format_attrs(match):
        if len(match.group(0)) <= linewidth:
            return match.group(0)

        space, tag, attrs, end = match.groups()
        indent = space + (len(tag) + 2) * ' '

        attrs = re.split('([a-zA-Z0-9-:_]+="[^"]*")', attrs)[1::2]
        attrs = [indent + attr for attr in attrs]
        attrs = '\n'.join(attrs).lstrip()

        return "{0}<{1} {2}{3}>".format(space,tag, attrs, end)

    string = etree.tostring(doc, pretty_print=True, encoding='utf-8',
                            xml_declaration=True)

    pattern = (
        '([ \t]*)'                  # Whitespace before the tag
        '<'                         # Tag start
            '([a-zA-Z0-9-:_]+)'     # Tag name
            '((?: '
                '[a-zA-Z0-9-:_]'    # Attribute name
                '+='
                '"[^"]*"'           # Attribute value
                '){2,})'            # Minimum two attributes
        '(/?)>'                     # Tag end
    )
    string = re.sub(pattern, format_attrs, string)

    return string
