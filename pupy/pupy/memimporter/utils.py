# -*- coding: utf-8 -*-

__all__ = ('package_context', 'find_writable_folder', 'load_library_common')

import ctypes

from os import path
from tempfile import gettempdir

import pupy

INITIALIZER = ctypes.PYFUNCTYPE(None)


class package_context(object):
    _Py_PackageContext = ctypes.c_char_p.in_dll(
        ctypes.pythonapi, '_Py_PackageContext')

    __slots__ = ('name', 'previous')

    def __init__(self, name):
        self.name = name
        self.previous = None

    def __enter__(self):
        self.previous = package_context._Py_PackageContext.value
        package_context._Py_PackageContext.value = self.name

    def __exit__(self, exc_type, exc_value, exc_traceback):
        package_context._Py_PackageContext.value = self.previous
        self.previous = None


def find_writable_folder(folders, validate=None):
    default_tmp = gettempdir()
    temporary_folders = tuple(folders)

    if default_tmp not in temporary_folders:
        temporary_folders += (default_tmp,)

    pupy.dprint(
        'find_writable_folder: possible folders: {}',
        temporary_folders
    )

    for folder in temporary_folders:
        if not path.isdir(folder):
            continue

        if validate is None:
            return folder

        if validate(folder):
            return folder


def load_library_common(
    fd, filepath, content, name,
        dlopen=False, initfuncname=None, post_load_hook=None):

    fd.write(content)
    fd.flush()

    if dlopen:
        handle = ctypes.CDLL(filepath)
        if post_load_hook:
            post_load_hook(handle, name)

        return handle

    if name.endswith(('.so', '.dll', '.pyd')):
        name = name.rsplit('.', 1)[0]

    module_name = name.split('.', 1)[-1]

    if initfuncname is None:
        initfuncname = 'init' + module_name

    try:
        lib = ctypes.PyDLL(filepath)
        pupy.dprint('load_library_common: Library loaded: {}', lib)
    except Exception as e:
        pupy.dprint('load_library_common: failed to load library {}: {}', name, e)
        lib = ctypes.CDLL(filepath)
        pupy.dprint('load_library_common: Library loaded: {} (fallback CDLL)', lib)

    if post_load_hook:
        post_load_hook(lib, name)

    initfunc = getattr(lib, initfuncname, None)

    if initfunc:
        pupy.dprint('load_library_common: init found: {}', initfunc)
        init = INITIALIZER(initfunc)

        with package_context(module_name):
            pupy.dprint(
                'load_library_common: call init {}@{}', initfuncname, module_name
            )
            init()
            pupy.dprint(
                'load_library_common: call init {}@{} - complete',
                initfuncname, module_name
            )

    return __import__(module_name)
