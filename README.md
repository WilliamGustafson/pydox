# Introduction
Pydox is a script to assemble `__doc__` strings in a given python
module into a pdf document using latex. The aim is to be simple to
use out of the box like [pydoc](https://docs.python.org/3/library/pydoc.html)
but to also provide more advanced formatting control such as
grouping documented objects into sections and controlling the order of
sections and objects. All `__doc__` strings are joined together into a
latex document so this script also gives you more control over
typsetting and lets you format equations, insert graphics, etc.
See [this project's documentation](https://github.com/WilliamGustafson/posets) for an example of the output of pydox.

Similar to the output of `pydoc` documentation created by `pydox` is
hierarchical. The documentation of each object is followed by the
documentation of each of its children, assuming it has any to be documented.
Documentation is only created for functions, classes and modules.
By default, only objects from the given module are documented and objects
defined outside the module are not documented. Wrapped functions,
such as those with a decorator, are handled specially. Only the inside
function is documented so there is no double listing and the argspec
is preserved.

As a warning, this codebase is still fragile and sloppy. That being
said, it seems to work well.

# Quick Start
`pydox` has a command line interface provided by [fire](https://github.com/google/python-fire). The following options are available:

- `--module` The module to be documented. This module must be importable.
- `--title` A title for the documentation, e.g. the module name, which is set via the latex commands `\title` and `\maketitle`. Defaults to `''` which adds no title.
- `--author` An author name, or names, to add to the title page. Defaults to `''` which adds no author names.
- `--date` A date to add to the title page. If this value is `True` today's date is added, if it is a string the string is set as the date. The default is `False` which adds no date.
- `--imp` A comma separated list of modules to import via `import x`. This allows you to import any modules needed for python embedded in your doc strings.
- `--impall` Like `--imp` but the modules are imported via `from x import *`.
- `--whitelist` A comma separated whitelist of modules, any objects not contained in a module from this whitelist will not be documented.
- `--outdir` The output directory to write the tex file to.
- `--preamble` Filename of a latex file containing the preamble for the document. The default preamble is`\documentclass[12pt]{article}\n\usepackage[margin=0.5in]{geometry}\n`.
- `--packages` A comma separated list of packages to include in the latex file via `\usepackage`. This can be the name of a local sty file (without the extension).
- `--post` Name of a latex file to include after the documentation. Useful for including a bibliography for example.
- `--compile` Whether to compile the document. If this is `True` the document is compiled twice with `pdflatex`, if this is `'bibtex'` the document is compiled once with `pdflatex`, then `bibtex` is called and `pdflatex` is called twice more. If this is `False`, the default, no compilation is performed.

In addition to having access to latex commands doc strings can make
use of a few commands from `pydox`. `pydox` uses a very simple parsing
scheme, the doc string is split up into blocks with `@` as the separator.
Then the blocks are read in order, any block that is the name of a command
is not written to output and the command is executed returning the
next block to parse and the output of said command which is written in
place of the command and any arguments. For example,
having `@section@Utilities@` in a doc string specifies that the object's
documentation will appear in a section named Utilities.
Note, to include the symbol `@` in your doc string without it being
parsed as a separator you can escape it with a backslash,
e.g. `\@`.
The available commands are:

- `section` Sets the name of this object's section, takes 1 argument and writes nothing.
- `section_key` Sets a key for this object's section for the purpose of sorting sections, takes 1 argument. The section key is interpreted as a string. If more than one object with the same section sets a section key it is undefined which of these values the section key will take.
- `sections_order` Sets the order of any sections below this object via specifying them by name. Takes a variable number of arguments, the arguments list is ended by an empty block e.g. `@sections_order@Operations@Queries@Utilities@@`.
- `sortkey` Sets a sort key for this object to sort it within its section. Objects with no key appear before those with a key. The key is interpreted as a string.
- `eval` The next block is evaluated as python and the result is written as a string in place of the two blocks.
- `exec` The next block is executed as python. No result is written for these two blocks. Both exec and eval commands share the same dictionary for locals.
- `no_list` This object will not be listed in the table of contents, takes no argument.
- `no_doc` This object will not be documented, any children of this object will still be documented. This command takes no argument.
- `is_section` This object will appear as a section, looks nice on classes. This command takes no argument.
- `no_children` No child of this object will be documented, takes no argument.
- `subclass` Marks the object as a subclass. Any attributes of this object that are also attributes of any base class (obtained via `obj.__bases__`) will not be documented; with an exception for the class's `__init__` method. This command takes no arguments.

# Known bugs and limitations

Setting a section on an ignored element, i.e. `@section@Whatever@no_doc@`
creates the section even if no other element is marked with that section.

