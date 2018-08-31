v8-project
==========

A set of tools to work with V8 JavaScript engine. In particular it takes care of all platform specific peculiarities when one has to obtain a new version of V8 or build it for a particular platform.

Getting the help
================

For a brief description of the available functionality run `build.py` without parameters.  
For a comprehensive overview of available commands and their options run `build.py --help`.  
Use `--help` to get detailed explaination of a command.


Getting V8
==========

In order to get V8 run `build.py sync`, one can optionally specify the revision of V8 by adding `--revision SOME_REVISION`.


Building V8
===========

In order to build V8 use the corresponding `build` command, e.g. `build.py build windows x64 debug`. The output is in the `{path to build.py}/build` directory.
