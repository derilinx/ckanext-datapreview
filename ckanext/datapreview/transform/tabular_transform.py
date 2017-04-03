"""Data Proxy - Messytables transformation adapter"""
import base
from ckanext.datapreview.lib.errors import ResourceError
from messytables import any_tableset, headers_guess, type_guess
from collections import defaultdict
import re

log = __import__('logging').getLogger(__name__)


HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}

class TabularTransformer(base.Transformer):

    def __init__(self, resource, url, query):
        super(TabularTransformer, self).__init__(resource, url, query)

        if 'worksheet' in self.query:
            self.sheet_number = int(self.query.getfirst('worksheet'))
        else:
            self.sheet_number = 0

        self.type = query.get('type')
        self.from_archive = query.get('archived', False)

        dataset_name = resource.resource_group.package.name \
            if resource.resource_group else '?'
        self.resource_identifier = '/dataset/%s/resource/%s' % (dataset_name, resource.id)

    def transform(self):
        handle = self.open_data(self.url)

        if not handle:
            raise ResourceError("Remote resource missing",
                                "Unable to load the remote resource")

        try:
            if self.is_csv():
                table_set = any_tableset(fileobj=handle,
                                         extension=self.type)
            else:
                table_set = any_tableset(fileobj=handle,
                                         extension=self.type,
                                         mimetype=self.mimetype)
        except Exception, e:
            # e.g. ValueError('Unrecognized MIME type: application/vnd.oasis.opendocument.spreadsheet')
            log.warn('Messytables parse error %s %s: %s', self.resource_identifier, self.url, e)
            log.warn('Some data: ext: %s, mime: %s', self.type, self.mimetype)
            raise ResourceError("Resource loading error",
                                "Unable to load the resource")

        tables = table_set.tables

        # Find a workable sheet with more than 0 rows
        rows = []
        for table in tables:
            # + 1 so that the header is included
            rows, more_results = _list(table, self.max_results + 1)
            if len(rows) > 0:
                break

        def prepare_cell(cell):
            v = unicode(cell)

            escaped_value = "".join(HTML_ESCAPE_TABLE.get(c,c) for c in v)

            #XXX ok, this is pretty Not A Good Idea
            # we're going to see if the cell has only numbers and , and .
            # and we'll just get rid of the commas in that case
            # seriously this is not really a great idea
            # what about numbers that use , as the decimal separator
            # or numbers that use , but don't have anything after the decimal place
            # etc etc etc
            remove_comma_separator_from_numbers(escaped_value)

            return escaped_value

        def remove_comma_separator_from_numbers(s):
            if re.match('^[ 0-9\.,]*$', s):
                s = s.replace(',', '')
            return s

        # Use the built-in header guessing in messytables to find the fields
        offset, headers = headers_guess(rows)
        fields = [prepare_cell(c) for c in headers] if headers else []

        # other rows become 'data'. Convert to unicode.
        # We should skip row offset so that we don't re-display the headers
        data = []
        for i, r in enumerate(rows[:self.max_results]):
            if i != offset:
                data.append([prepare_cell(c.value.strip()) for c in r])

        # we're going to guess the field types here
        # looks like:
        # { field_name: {"position": 0, "dimensionality": "scalar", "datatype": "int"}... }

        field_types = {}

        # XXX same as above, this is terrible and I should be fired
        rows_for_type_guess = rows
        for row in rows_for_type_guess:
            for c in row:
                c.value = remove_comma_separator_from_numbers(c.value)
        guessed_types = type_guess(rows_for_type_guess)

        for i, f in enumerate(fields):
            field_types[f] = {
                "position": i,
                "datatype": str(guessed_types[i]),
            }

            # datatype one of
            #String, Decimal, Integer, Date, Bool, Time, Currency, Percentage

            #XXX this whole thing is super inefficient. don't ship any of it.

            # get all the cells of this field

            if (field_types[f]['datatype'] == 'String'):
                data_dict = []
                #get the data dict for this field
                #XXX super inefficient
                # btw for future, to check whether a column only has unique fields,
                for row in data:
                    for j, c in enumerate(row):
                        if i == j and c != '':
                            data_dict.append(c)
                data_dict_set = set(data_dict)
                field_types[f]['data_dict'] = list(data_dict_set)
                # if not len(data_dict) == len(data_dict_set) and len(data_dict) > 1:
                #     field_types[f]['data_dict'] = list(data_dict_set)
                # else:
                #     field_types[f]['identifier'] = True
            # elif field_types[f]['datatype'] in ['Integer', 'Float', 'Decimal']:
            #     total = 0

            #     for row in data:
            #         for j, c in enumerate(row):
            #             if i == j:
            #                 total += float(c if c else 0)

            #     field_types[f]['total'] = total
            #     field_types[f]['average'] = total/len(data)

        extra = ""

        if len(tables) > 1:
            extra = "Only 1 of {0} tables shown".format(len(tables))
            if more_results:
                extra = extra + " and the first {0} rows in this table".format(self.max_results)
        else:
            if more_results:
                extra = "This preview shows only the first {0} rows - download it for the full file".format(self.max_results)

        data_dictionary = {}

        result = {
            "fields": fields,
            "field_info": field_types,
            "data": data,
            "max_results": self.max_results,
            "extra_text": extra,
            "archived": "This file is previewed from the archive." if self.from_archive else ""
        }

        self.close_stream(handle)

        return result

    def requires_size_limit(self):
        if self.is_csv():
            # We are confident that messytables.CSVTableSet will give us a
            # sample of the data without having to load the whole of the file
            # into memory, so we lift the size limit
            return False
        else:
            return True

    def is_csv(self):
        '''This should catch most files for which messytables.any_tableset will
        use CSVTableSet to parse them.
        '''
        if self.type.lower() in ['csv', 'tsv']:
            return True

        if self.mimetype and self.mimetype.lower() in \
           ['text/csv', 'text/comma-separated-values', 'application/csv']:
            return True

        return False

def _list(iterable, max_results):
    '''Returns the list(iterable) up to a maximum number of results'''
    out = []
    more_results = False
    count = 0
    for item in iterable:
        if count > max_results:
            more_results = True
            break
        out.append(item)
        count += 1
    return out, more_results
