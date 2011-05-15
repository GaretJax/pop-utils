from lxml import etree

class AWSException(object):
    def __init__(self, exc):
        self.original = exc
        self.doc = etree.fromstring(exc.body)

        if len(self.doc.xpath('Response/Errors/Error')) > 1:
            raise NotImplementedError("Multiple errors are not yet supported")

    @property
    def code(self):
        return self.doc.xpath('/Response/Errors/Error/Code/text()')[0]

    @property
    def message(self):
        return self.doc.xpath('/Response/Errors/Error/Message/text()')[0]

    @property
    def requestID(self):
        return self.doc.xpath('/Response/RequestID/text()')[0]