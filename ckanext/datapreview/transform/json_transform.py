"""Data Proxy - JSON transformation adapter"""
from ckanext.datapreview.transform.base import Transformer
from ckanext.datapreview.lib.errors import ResourceError
import json

MAX_TEXT_SIZE = 819200

class JSONTransformer(Transformer):
    """
just returns json
    """
    def __init__(self, resource, url, query):
        super(JSONTransformer, self).__init__(resource, url, query)

    def transform(self):
        handle = self.open_data(self.url)
        if not handle:
            import requests
            return {'data': json.loads(requests.get(self.url).content)}
        #    raise ResourceError("Remote resource missing",
        #                        "Unable to load the remote resource")

        data = handle.read(MAX_TEXT_SIZE)
        data = data.decode('utf-8', 'ignore')
        result = {}
        result['data'] = json.loads(data)
        self.close_stream(handle)

        return result
