#!/usr/bin/python
# coding=UTF-8

import logging
import plistlib
import os.path
import json
import uuid
from .jsonfile import JsonFile
from xml.etree.ElementTree import Element, SubElement, tostring


LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(name)s: %(message)s'
LOG = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(__file__)


def _check_dir_writeable(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        if not os.access(path, os.W_OK):
            raise IOError('No write access to %s' % path)


def _run_script(script):
    from subprocess import Popen, PIPE
    p = Popen(['osascript', '-ss', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    LOG.debug('communicating {0}'.format(script))
    stdout, stderr = p.communicate(script)
    return stdout.decode('utf-8'), stderr.decode('utf-8')


class Item(object):
    LINE = unichr(0x2500) * 20

    '''An item in an Alfred feedback XML message'''

    def __init__(self, title, subtitle=None, icon=None, valid=False, arg=None,
                 uid=None, random_uid=False, autocomplete=None, prefix=None):
        self.title = title
        self.subtitle = subtitle
        self.icon = icon if icon is not None else 'icon.png'
        self.uid = uid
        self.valid = valid
        self.arg = arg
        self.prefix = prefix
        self.autocomplete = autocomplete

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
        item = Element('item')

        if self.uid:
            item.set('uid', self.uid)

        if self.valid:
            item.set('valid', 'yes')
        else:
            item.set('valid', 'no')

        if self.autocomplete:
            ac = self.autocomplete
            if self.prefix:
                ac = self.prefix + ' ' + ac
            item.set('autocomplete', ac)

        if self.arg is not None:
            item.set('arg', self.arg)

        title = SubElement(item, 'title')
        title.text = self.title

        if self.subtitle is not None:
            subtitle = SubElement(item, 'subtitle')
            subtitle.text = self.subtitle

        if self.icon is not None:
            icon = SubElement(item, 'icon')

            if isinstance(self.icon, dict):
                icon.set('type', self.icon['type'])
                icon.text = self.icon['path']
            else:
                icon.text = self.icon

        return tostring(item)

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
        self._config = None

    def __str__(self):
        return self.name

    @property
    def id(self):
        if not hasattr(self, '_id'):
            from os.path import basename
            self._id = basename(self.path).split('.')[2]
        return self._id

    @property
    def config(self):
        if not self._config:
            try:
                self._config = JsonFile(self.config_file)
            except ValueError:
                self._config = {}
                LOG.error('Error loading config file')
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


class MenuItem(object):
    def __init__(self, command, text):
        self.command = command
        self.text = text

    def to_item(self, prefix=None):
        ac = prefix + ' ' if prefix else ''
        ac += self.command + ' '
        return Item(self.command, autocomplete=ac, subtitle=self.text)


class Command(MenuItem):
    pass


class Keyword(MenuItem):
    def __init__(self, command, text, arg=None):
        super(Keyword, self).__init__(command, text)
        self.arg = arg if arg else command

    def to_item(self, prefix=None):
        item = super(Keyword, self).to_item(prefix)
        item.arg = self.arg
        item.valid = True
        return item


class Menu(Command):
    pass


class Workflow(object):

    def __init__(self):
        self._info = WorkflowInfo()

        _check_dir_writeable(self.data_dir)
        _check_dir_writeable(self.cache_dir)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(getattr(logging, self.log_level))

    @property
    def config(self):
        return self._info.config

    @property
    def config_file(self):
        return self._info.config_file

    @property
    def log_level(self):
        return self.config.get('loglevel', 'DEBUG')

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
        from sys import stdout
        stdout.write(msg.encode('utf-8'))

    def menu(self, structure, query, prefix=None):
        '''Manage a structured menu'''
        query = query.lstrip()
        items = []

        LOG.debug('menu with query "%s" and prefix %s', query, prefix)

        for entry in structure:
            items.append(entry.to_item(prefix))

        if len(query) > 0:
            if ' ' in query:
                command, sep, args = query.partition(' ')

                # query contains a space, so look for an exact match for the
                # command word
                items = self.match_list(command, items, key=lambda t: t.title)
                if len(items) > 1:
                    items = [Item('Multiple commands match "{0}"'.format(
                                  command))]
                elif len(items) == 1:
                    item = items[0]
                    if not item.arg:
                        # the item doesn't have an argument, # so it must be a
                        # filter entry
                        return getattr(self, 'tell_' + command)(args.lstrip(),
                                                                prefix=command)
                    elif len(args.strip()) > 0:
                        items = [Item('"{0}" command doesn\'t take '
                                      'arguments'.format(command))]
            else:
                # query doesn't end with a space, so find anything that matches
                items = self.partial_match_list(query, items,
                                                key=lambda t: t.title)

        if len(items) == 0:
            items.append(Item('No commands match "{0}"'.format(query)))

        return items

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

    def partial_match(self, test, text, words=False, ordered=True):
        '''Return true if the given text partially matches the test'''
        return text.lower().startswith(test.lower())

    def match_list(self, test, items, matcher=None, key=None, words=False,
                   ordered=True):
        '''Return the subset of items that match a string [test]'''
        matches = []
        for item in items:
            if key:
                istr = key(item)
            else:
                istr = str(item)

            is_match = False
            if matcher:
                is_match = matcher(test, istr, words=words, ordered=ordered)
            else:
                is_match = test == istr
            if is_match:
                matches.append(item)
        return matches

    def fuzzy_match_list(self, test, items, key=None, words=False,
                         ordered=True):
        '''Return the subset of items that fuzzy match a string [test]'''
        return self.match_list(test, items, self.fuzzy_match, key, words,
                               ordered)

    def partial_match_list(self, test, items, key=None, words=False,
                           ordered=True):
        '''Return the subset of items that partially match a string [test]'''
        return self.match_list(test, items, self.partial_match, key, words,
                               ordered)

    def to_xml(self, items):
        '''Convert a list of Items to an Alfred XML feedback message'''
        msg = [u'<?xml version="1.0"?>', u'<items>']

        for item in items:
            msg.append(item.to_xml())

        msg.append(u'</items>')
        return u''.join(msg)

    def run_script(self, script):
        '''Run an AppleScript, returning its output'''
        return _run_script(script)

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

        stdout, stderr = self.run_script(script)
        response = stdout.rstrip('\n')
        button, sep, value = response.partition('|')
        return (button, value)

    @classmethod
    def get_selection_from_user(cls, title, prompt, choices, default=None,
                                multiple=False):
        '''Popup a dialog to let a user select a value from a list of choices.

        The main use for this function is to request information that you don't
        want showing up in Alfred's command history.
        '''
        if default is None:
            default = ''

        if not isinstance(choices, (tuple, list)):
            choices = [choices]
        choices = '{{"{0}"}}'.format('","'.join(choices))

        if multiple:
            multiple = 'with'
        else:
            multiple = 'without'

        with open(os.path.join(BASE_DIR, 'get_selection.scpt')) as sfile:
            script = sfile.read().format(default=default, prompt=prompt,
                                         title=title, choices=choices,
                                         multiple=multiple)
        stdout, stderr = _run_script(script)
        LOG.debug('stdout: %s', stdout)
        LOG.debug('stderr: %s', stderr)
        response = stdout.rstrip('\n').strip('"')
        button, sep, value = response.partition('|')
        if button == 'Cancel':
            return None
        return value

    def get_confirmation(self, title, prompt, default='No'):
        '''Display a confirmation dialog'''
        with open(os.path.join(BASE_DIR, 'get_confirmation.scpt')) as sfile:
            script = sfile.read().format(p=prompt, t=title, d=default)
        stdout, stderr = _run_script(script)
        if len(stderr) > 0:
            raise Exception(stderr)
        return stdout.rstrip('\n').strip('"')

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

        return self.run_script(script)

    def tell(self, name, query=''):
        '''Tell something.'''
        LOG.debug('tell(%s, %s)', name, query)
        try:
            cmd = 'tell_%s' % name
            if getattr(self, cmd):
                items = getattr(self, cmd)(query)
            else:
                items = [Item('Invalid action "%s"' % name)]
        except Exception as e:
            LOG.exception('Error telling')
            items = [Item('Error: %s' % e)]
        self.puts(self.to_xml(items))

    def do(self, name, query='', modifier=None):
        '''Do something.'''
        try:
            cmd = 'do_%s' % name
            doer = getattr(self, cmd)
            if doer:
                if modifier:
                    doer(query, modifier)
                else:
                    doer(query)
            else:
                self.puts('Invalid command "%s"' % name)
        except Exception as e:
            LOG.exception('Error showing')
            self.puts('Error: %s' % e)


if __name__ == '__main__':
    from sys import argv
    getattr(Workflow, argv[1])(*argv[2:])
