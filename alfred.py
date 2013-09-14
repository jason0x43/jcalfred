#!/usr/bin/python
# coding=UTF-8

import logging
import plistlib
import os.path
import json
import uuid
from logging import handlers
from sys import stdout
from xml.sax.saxutils import escape


LINE = unichr(0x2500) * 20
LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(name)s: %(message)s'
LOG = logging.getLogger(__name__)


def _check_dir_writeable(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        if not os.access(path, os.W_OK):
            raise IOError('No write access to %s' % path)


class Item(object):
    '''An item in an Alfred feedback XML message'''
    def __init__(self, title, subtitle=None, icon=None, valid=False, arg=None,
                 uid=None, random_uid=True):
        self.title = title
        self.subtitle = subtitle
        self.icon = icon if icon is not None else 'icon.png'
        self.uid = uid
        self.valid = valid
        self.arg = arg

        if not uid and random_uid:
            self.uid = str(uuid.uuid4())

    @classmethod
    def from_dict(cls, obj):
        return Item(title=obj['title'],
                    subtitle=obj['subtitle'],
                    icon=obj['icon'],
                    uid=obj['uid'],
                    valid=obj['valid'],
                    arg=obj['arg'])

    def to_xml(self):
        attrs = []

        attrs.append(u'uid="%s"' % self.uid)

        if self.valid:
            attrs.append('valid="yes"')
        else:
            attrs.append('valid="no"')

        if self.arg is not None:
            attrs.append(u'arg="%s"' % self.arg)

        xml = [u'<item %s>' % (u' '.join(attrs))]

        title = escape(self.title)
        xml.append(u'<title>%s</title>' % title)

        if self.subtitle is not None:
            subtitle = escape(self.subtitle)
            xml.append(u'<subtitle>%s</subtitle>' % subtitle)
        if self.icon is not None:
            if isinstance(self.icon, dict):
                xml.append(u'<icon type="%s">%s</icon>' % (
                    self.icon['type'], self.icon['path']))
            else:
                xml.append(u'<icon>%s</icon>' % self.icon)

        xml.append(u'</item>')
        return ''.join(xml)

    def to_dict(self):
        return {
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'uid': self.uid,
            'valid': self.valid,
            'arg': self.arg
        }

    def __str__(self):
        return '{{Item: title="%s", valid=%s, arg="%s"}}' % (
            self.title.encode('utf-8'), self.valid, self.arg)

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return self.__str__()


class JsonFile(object):
    def __init__(self, path, default_data=None, ignore_errors=False):
        self._data = {}
        self._path = path

        if os.path.exists(path):
            try:
                with open(path, 'rt') as cfile:
                    self._data = json.load(cfile)
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

    def get(self, key, default=None):
        return self._data.get(key, default)

    def _save(self):
        with open(self._path, 'wt') as cfile:
            json.dump(self._data, cfile, indent=2)


class WorkflowInfo(object):
    def __init__(self, path=None):
        if not path:
            path = os.getcwd()

        self.bundle = plistlib.readPlist(os.path.join(path, 'info.plist'))
        self.path = path
        self.bundle_id = self.bundle['bundleid']

        self._cache_dir = os.path.expanduser(
            '~/Library/Caches/com.runningwithcrayons.Alfred-2'
            '/Workflow Data/%s' % self.bundle_id)
        self._data_dir = os.path.expanduser(
            '~/Library/Application Support/Alfred 2/Workflow Data/%s' %
            self.bundle_id)

        self.icon = os.path.join(path, 'icon.png')
        self.name = self.bundle['name']
        self.readme = self.bundle['readme']
        self.config_file = os.path.join(self.data_dir, 'config.json')
        self.update_file = os.path.join(path, 'update.json')
        self._config = JsonFile(self.config_file)

    def __str__(self):
        return self.name

    @property
    def config(self):
        return self._config

    @property
    def update_info(self):
        if not hasattr(self, '_update_info'):
            if os.path.exists(self.update_file):
                with open(self.update_file) as uf:
                    self._update_info = json.load(uf)
            else:
                self._update_info = None
        return self._update_info

    @property
    def data_dir(self):
        return self._data_dir

    @property
    def cache_dir(self):
        return self._cache_dir


class Workflow(object):
    def __init__(self):
        self._info = WorkflowInfo()

        _check_dir_writeable(self.data_dir)
        _check_dir_writeable(self.cache_dir)

        self._log_file = os.path.join(self.cache_dir, 'debug.log')
        handler = handlers.TimedRotatingFileHandler(
            self._log_file, when='H', interval=1, backupCount=1)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(getattr(logging, self.log_level))

    @property
    def config(self):
        return self._info.config

    @property
    def log_level(self):
        return self.config.get('loglevel', 'INFO')

    @property
    def log_file(self):
        return self._log_file

    @log_level.setter
    def log_level(self, level):
        self.config['loglevel'] = level
        logging.getLogger().setLevel(getattr(logging, level))

    @property
    def info(self):
        return self._info

    @property
    def bundle_id(self):
        return self._info.bundle_id

    @property
    def data_dir(self):
        return self._info.data_dir

    @property
    def cache_dir(self):
        return self._info.cache_dir

    def puts(self, msg):
        '''Output a string.'''
        stdout.write(msg.encode('utf-8'))

    def fuzzy_match(self, test, text, words=False, ordered=True):
        '''Return true if the given text fuzzy matches the test'''
        start = 0
        test = test.lower()
        text = text.lower()

        if words:
            tokens = test.split()
        else:
            tokens = list(test)

        if ordered:
            for c in tokens:
                i = text.find(c, start)
                if i == -1:
                    return False
                start = i + 1
        else:
            for c in tokens:
                if c not in text:
                    return False
        return True

    def fuzzy_match_list(self, test, items, key=None, words=False,
                         ordered=True):
        '''Return the subset of items that fuzzy match a string [test]'''
        matches = []
        for item in items:
            if key:
                istr = key(item)
            else:
                istr = str(item)

            if self.fuzzy_match(test, istr, words=words, ordered=ordered):
                matches.append(item)
        return matches

    def to_xml(self, items):
        '''Convert a list of Items to an Alfred XML feedback message'''
        msg = [u'<?xml version="1.0"?>', u'<items>']

        for item in items:
            msg.append(item.to_xml())

        msg.append(u'</items>')
        return u''.join(msg)

    def run_script(self, script):
        '''Run an AppleScript, returning its output'''
        from subprocess import Popen, PIPE
        p = Popen(['osascript', '-ss', '-'], stdin=PIPE, stdout=PIPE,
                  stderr=PIPE)
        stdout, stderr = p.communicate(script)
        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def show_log(self):
        '''Open the debug log in the system default viewer'''
        from subprocess import call
        call(['open', self.log_file])

    def get_from_user(self, title, prompt, hidden=False, value=None,
                      extra_buttons=None):
        '''Popup a dialog to request some piece of information.

        The main use for this function is to request information that you don't
        want showing up in Alfred's command history.
        '''
        if value is None:
            value = ''

        buttons = ['Cancel', 'Ok']
        if extra_buttons:
            if isinstance(extra_buttons, (list, tuple)):
                buttons = extra_buttons + buttons
            else:
                buttons.insert(0, extra_buttons)
        buttons = '{%s}' % ', '.join(['"%s"' % b for b in buttons])

        hidden = 'with hidden answer' if hidden else ''

        script = '''
            on run argv
              tell application "Alfred 2"
                  activate
                  set alfredPath to (path to application "Alfred 2")
                  set alfredIcon to path to resource "appicon.icns" in bundle ¬
                    (alfredPath as alias)

                  try
                    display dialog "{p}:" with title "{t}" ¬
                      default answer "{v}" ¬
                      buttons {b} default button "Ok" with icon alfredIcon {h}
                    set answer to (button returned of result) & "|" & ¬
                      (text returned of result)
                  on error number -128
                    set answer to "Cancel|"
                  end
              end tell
            end run'''.format(v=value, p=prompt, t=title, h=hidden, b=buttons)

        from subprocess import Popen, PIPE
        p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(script)
        response = stdout.decode('utf-8').rstrip('\n')
        button, sep, value = response.partition('|')
        return (button, value)

    def get_confirmation(self, title, prompt, default='No'):
        '''Display a confirmation dialog'''
        script = '''
            on run argv
              tell application "Alfred 2"
                  activate
                  set alfredPath to (path to application "Alfred 2")
                  set alfredIcon to path to resource "appicon.icns" in bundle ¬
                    (alfredPath as alias)

                  try
                    display dialog "{p}" with title "{t}"  ¬
                      buttons {{"Yes", "No"}} default button "{d}" ¬
                      with icon alfredIcon
                    set answer to (button returned of result)
                  on error number -128
                    set answer to "No"
                  end
              end tell
            end run'''.format(p=prompt, t=title, d=default)

        from subprocess import Popen, PIPE
        p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(script)
        return stdout.decode('utf-8').rstrip('\n')

    def show_message(self, title, message):
        '''Display a message dialog'''
        script = '''
            on run argv
              tell application "Alfred 2"
                  activate
                  set alfredPath to (path to application "Alfred 2")
                  set alfredIcon to path to resource "appicon.icns" in bundle ¬
                    (alfredPath as alias)

                  display dialog "{m}" with title "{t}" buttons ¬
                    {{"Ok"}} default button "Ok" with icon alfredIcon
              end tell
            end run'''.format(t=title, m=message)

        from subprocess import Popen, PIPE
        p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.communicate(script)

    def tell(self, name, query=''):
        '''Tell something.'''
        LOG.debug('tell(%s, %s)', name, query)
        try:
            cmd = 'tell_%s' % name
            if getattr(self, cmd):
                items = getattr(self, cmd)(query)
            else:
                items = [Item('Invalid action "%s"' % name)]
        except Exception, e:
            LOG.exception('Error telling')
            items = [Item('Error: %s' % e)]
        self.puts(self.to_xml(items))

    def do(self, name, query=''):
        '''Do something.'''
        try:
            cmd = 'do_%s' % name
            if getattr(self, cmd):
                getattr(self, cmd)(query)
            else:
                self.puts('Invalid command "%s"' % name)
        except Exception, e:
            LOG.exception('Error showing')
            self.puts('Error: %s' % e)


if __name__ == '__main__':
    from sys import argv
    globals()[argv[1]](*argv[2:])
