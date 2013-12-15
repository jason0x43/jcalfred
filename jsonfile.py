import logging
import json
import os.path


LOG = logging.getLogger(__name__)


class JsonFile(object):
    def __init__(self, path, default_data=None, ignore_errors=False,
                 header=None):
        '''Construct a new JsonFile.

        Parameters
        ----------
        default_data : dict
            This is a dictionary of data to initialize the JsonFile with. Any
            data already present in the file will override this data.

        ignore_errors : boolean
            Set to True to ignore errors when loading data from an existing
            file.

        header : string
            A comment header to include with the file. This should be a string
            or a list of strings. Necessary comment tags will be added
            automatically.
        '''
        self._data = {}
        self._path = path
        self._header = header

        if os.path.exists(path):
            try:
                with open(path, 'rt') as cfile:
                    lines = [n for n in cfile.readlines() if not
                             n.strip().startswith('//')]
                    self._data = json.loads(''.join(lines))
            except ValueError:
                if ignore_errors:
                    LOG.warn('ignoring corrupt JsonFile %s', path)
                    self._data = {}
                else:
                    LOG.warn('corrupt JsonFile %s', path)
                    raise
        elif default_data:
            self._data = default_data
            self._save()

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        self._save()

    def __setitem__(self, key, value):
        self._data[key] = value
        self._save()

    def __iter__(self):
        return self._data.__iter__()

    def iterkeys(self):
        return self._data.__iter__()

    def items(self):
        return self._data.items()

    @property
    def path(self):
        return self._path

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, value):
        self._header = value
        self._save()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def _save(self):
        with open(self._path, 'wt') as cfile:
            if self.header:
                if not isinstance(self.header, (list, tuple)):
                    self.header = self.header.split('\n')
                for line in self.header:
                    cfile.write('// {0}\n'.format(line))
            json.dump(self._data, cfile, indent=2)
