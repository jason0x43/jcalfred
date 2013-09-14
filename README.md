Python package for developing [Alfred 2][alfred] Workflows
==========================================================

This package has a few utility functions that I developed while writing Alfred
workflows. Take a look at the source for more information.

Workflow structure
------------------

I tend to structure my workflows like this:

     +---------------+         +------------+        +-------------------+
     |   keyword 1   |         |   python   |        |                   |
     |               |---------|  action 1  |--------| Post Notification |
     | Script Filter |         | Run Script |    /   |                   |
     +---------------+         +------------+    |   +-------------------+
                                                 |
     +---------------+         +------------+    |
     |   keyword 2   |         |   python   |    |
     |               |---------|  action 2  |----/
     | Script Filter |         | Run Script |
     +---------------+         +------------+

Or sometimes like this:

     +---------------+         +------------+        +-------------------+
     |   keyword 1   |         |   python   |        |                   |
     |               |---------|  action 1  |--------| Post Notification |
     | Script Filter |     /   | Run Script |        |                   |
     +---------------+     |   +------------+        +-------------------+
                           |
     +---------------+     |
     |   keyword 2   |     |
     |               |-----/
     | Script Filter |        
     +---------------+        

     +---------------+
     |   keyword 3   |
     |               |
     | Script Filter |        
     +---------------+        

Keywords are always handled by Script Filters, which can be used to give
immediate feedback. The script filters feed into one or more Run Scripts that
take some action. Sometimes keywords don't feed into actions, because immediate
feedback is all that's needed.

### Keywords

The code in Keyword blocks usually looks like:

```python
from alfred_something import SomeWorkflow
SomeWorkflow().tell('a_thing', '''{query}''')
```

This just instantiates one of your Workflow objects (described later) and calls
`tell` for a particular function.

### Actions

Actions are implemented by Run Script blocks. Their code looks very similar to
the keyword blocks:

```python
from alfred_something import SomeWorkflow
SomeWorkflow().do('an_action', '''{query}''')
```


What this library provides
--------------------------

### alfred.py

The `alfredy.py` module has a `Workflow` class that eases the task of
creating workflows that handle user input and provide instant feedback. As
described abive, I architect workflows around `tell` and `do` methods. The
`tell` methods (e.g., `tell_temperature`) run in a Script Filter task and
return a list of `Item` objects for instant feedback. The `do` methods run in a
Run Script task and take some action, potentially displaying output in a Post
Notification task. The Workflow class has archetypal `do()` and `tell()`
methods that will call the proper specialized method in a sublass and display
any raised exceptions in a reasonable way.

A very simple example workflow for getting and setting the temperature for a
Nest thermostat might look something like:

```python
from jcalfred import Workflow, Item
from my_nest_lib import get_nest_temperature, set_nest_temperature

class NestWorkflow(Workflow):
    def tell_temperature(self, query):
        temp = get_nest_temperature()
        return [Item('Temperature: {}&deg;F'.format(temp)')]

    def do_temperature(self, temp):
        set_nest_temperature(temp)
        self.puts('Set temperature to {}&deg;F'.format(temp)')
```

The Script Filter block would call `tell_temperature` with:

```python
from nest_workflow import NestWorkflow
NestWorkflow().tell('temp')
```

There's no need for the query argument in this case since any user input will
just be ignored.

Similarly, the Run Script block would call `do_temperature` with:

```python
from nest_workflow import NestWorkflow
NestWorkflow().do('temp', '''{query}''')
```

#### Item

The `Item` class encapsulates a single item displayed by Alfred.

##### Properties

* `title` - the title (big text)
* `subtitle` - the subtext
* `icon` - the icon; if none is specified, Alfred will use the workflow's icon
* `uid` - a unique ID for this item; setting this to a consistent value for a
  particular item will let Alfred learn how frequently you access that item
* `valid` - True of this item can be actioned
* `arg` - the argument that will be passed on when this item is actioned

#### Workflow

The `Workflow` class handles converting the `Items` returned by
`tell_temperature` into an XML doc for Alfred. It will also catch any
exceptions thrown in the do or tell methods and return them in the proper
format (as XML or text) for them to show up to the user.

##### Properties

* `config` - a persistent dictionary of settings
* `data_dir` - the directory where the workflow should store persistent data
* `cache_dir` - the directory where the workflow should store more transient
information
* `log_level` - logging.{DEBUG, INFO, ...}
* `log_file` - the absolute path of the workflow debug log file

##### Methods

* `puts(string)` - a method to write an ASCII or Unicode string to stdout
* `fuzzy_match(test, text, words=True, ordered=True)` - return true if a given
text fuzzy matches a given test string
* `fuzzy_match_list(test, items, key=None, words=False, ordered=True)` - fuzzy
match a given test against a list of strings
* `get_from_user(title, prompt, hidden=False, value=None,
extra_buttons=None)` - open a dialog to get a string from the user
* `get_confirmation(title, prompt, default='No')` - open a dialog with yes/no
buttons
* `show_message(title, message)` - open a dialog to display a short message

#### JsonFile

`JsonFile` is a live...err, JSON file. Point it at a file when it's
instantiated and it will translate between a Python dict and a JSON file. This
only works from within the app using the `JsonFile`, though; it doesn't detect
external modifications.

The only interesting property for this class is `path`, which returns the path
being used by the file. Otherwise it basically looks like a `dict`.

### keychain.py

The `keychain.py` module provides very simplified access to the Mac OSX
Keychain. It only has three functions: `get_item`, `set_item`, and `del_item`.
Keys are identified by account name and service name. The service name is the
name of the workflow or application ("jcalfred" by default). The account name
is the name of the specific service/site/whatever that the password is for. You
may also specify an arbitrary comment string when setting a password.

The `get_item` function returns a `dict` with the keys "service", "account",
"password", and "comment".

[alfred]: http://www.alfredapp.com
