

import os
from lxml import etree


def schema(name):
    """
    Retrieves a schema by name from the 'schemata' directory and wraps it in an
    lxml.etree.XMLSchema object.
    """
    schema = os.path.join(os.path.dirname(__file__), 'schemata', name + '.xsd')
    document = etree.parse(schema) # Will raise if schema does not exist
    return etree.XMLSchema(document)