import sys
from ckanext.datapreview.transform.base import *
from ckanext.datapreview.transform.tabular_transform import TabularTransformer
from ckanext.datapreview.transform.plain_transform import PlainTransformer
from ckanext.datapreview.transform.json_transform import JSONTransformer

register_transformer({
        "name": "csv",
        "class": TabularTransformer,
        "extensions": ["csv", "tsv", "xls", "ods"],
        "mime_types": ("text/csv", "text/comma-separated-values", "application/excel", "application/vnd.ms-excel")
    })

register_transformer({
        "name": "txt",
        "class": PlainTransformer,
        "extensions": ["txt", "plain"],
        "mime_types": ("text/plain",),
    })

register_transformer({
        "name": "json",
        "class": JSONTransformer,
        "extensions": ["json-stat", "json", "geojson"],
        "mime_types": ("application/json",),
    })

