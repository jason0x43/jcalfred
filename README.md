Python package for developing [Alfred 2][alfred] Workflows
==========================================================

This package has a few utility functions that I developed while writing Alfred
workflows. Take a look at the source for more information.

alfred.py
---------

The `alfredy.py` module has an `AlfredWorkflow` class that eases the task of
creating workflows that handle user input and provide instant feedback. The way
I architect workflows is based on "tell" and "do" methods. The "tell" methods
(e.g., `tell_temperature`) run in a Script Filter task and return a list of
`Item` objects for instant feedback. The "do" methods run in a Run Script task
and take some action, potentially displaying output in a Post Notification
task. The AlfredWorkflow class has archetypal `do()` and `tell()` methods that
will call the proper specialized method in a sublass and display any raised
exceptions in a reasonable way.

A very simple example workflow might look something like:

    import jcalfred

    class Workflow(jcalfred.AlfredWorkflow):
        def tell_temperature(self, query):
            temp = get_nest_temperature()
            return [jcalfred.Item('Temperature: {}&deg;F'.format(temp)')]

        def do_temperature(self, temp):
            set_nest_temperature(temp)
            self.puts('Set temperature to {}&deg;F'.format(temp)')

keychain.py
-----------

The `keychain.py` module provides very simplified access to the Mac OSX
Keychain. It only has three functions: `get_item`, `set_item`, and `del_item`.
Keys are identified by account name and service name. The service name is the
name of the workflow or application ("jcalfred" by default). The account name
is the name of the specific service/site/whatever that the password is for. You
may also specify an arbitrary comment string when setting a password.

The `get_item` function returns a `dict` with the keys "service", "account",
"password", and "comment".
