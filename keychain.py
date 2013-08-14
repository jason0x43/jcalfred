#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Access the Mac OS X keychain.

This script was inspired by Stever Webster's keychain.py (https://github.com/
spjwebster/keychain.py), which was originally based on Stuart Colville's
Keychain.py. It's has fewer features than either of the others, but I didn't
really need to do much other than get and set passwords.
'''

import sys
from subprocess import check_output, call, CalledProcessError, STDOUT


DEFAULT_SERVICE = 'jcalfred'


TAG_NAMES = {
    'svce': 'service',
    'acct': 'account',
    'icmt': 'comment',
}


if sys.platform != 'darwin':
    raise Exception('This library only works on Mac OS X')


class Keychain(object):
    def __init__(self, service=DEFAULT_SERVICE):
        self._service = service

    @property
    def service(self):
        return self._service

    def _parse_keychain_item(self, lines):
        '''Parse a keychain item.'''
        item = {'service': None, 'account': None, 'comment': None,
                'password': None}
        for line in lines:
            if line.startswith('password: '):
                ipass = line[10:].strip().strip('"')
                item['password'] = ipass
            elif line.startswith(' '):
                line = line.strip()
                if line.startswith('0'):
                    tag, sep, val = line.partition(' ')
                    vtype, sep, val = val.partition('=')
                else:
                    tag, sep, val = line.partition('<')
                    tag = tag.strip('"')
                    vtype, sep, val = val.partition('=')

                if val == '<NULL>':
                    continue

                if tag in TAG_NAMES:
                    item[TAG_NAMES[tag]] = val.strip('"')
        return item

    def get_password(self, account):
        '''Retrieve a password entry.

        account   the account password to get
        service   (optional) service name for the password
        '''
        cmd = ['security', 'find-generic-password', '-g', '-a', account, '-s',
               self._service]

        try:
            out = check_output(cmd, stderr=STDOUT)
            item = self._parse_keychain_item(out.split('\n'))
            return item
        except CalledProcessError:
            return None

    def set_password(self, account, password, comment=None):
        '''Add or update a password entry.

        account    the name of the account the password is for (e.g., plugin
                   name)
        password   the password value
        comment    (optional) text to be stored with password
        service    (optional) the service the password is for
        '''
        label = '%s.%s' % (self._service, account)
        cmd = ['security', 'add-generic-password', '-w', password, '-a',
               account, '-s', self._service, '-U', '-l', label]
        if comment:
            cmd += ['-j', comment]

        try:
            call(cmd)
        except CalledProcessError:
            return None

    def del_password(self, account):
        '''Delete a password entry.

        account    the name of the account the password is for (e.g., plugin
                   name)
        service    (optional) the service the password is for
        '''
        cmd = ['security', 'delete-generic-password', '-a', account, '-s',
               self._service]
        check_output(cmd, stderr=STDOUT)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('get', 'set', 'del'))
    parser.add_argument('account')
    args = parser.parse_args()

    keychain = Keychain()

    if args.command == 'get':
        print keychain.get_password(args.account)
    elif args.command == 'set':
        from getpass import getpass
        passwd = getpass('Password: ')
        keychain.set_password(args.account, passwd)
    elif args.command == 'del':
        keychain.del_password(args.account)
