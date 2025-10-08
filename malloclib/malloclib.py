import os
import sys
import shlex
from functools import cache
from ctypes import CDLL, c_size_t, c_void_p
from typing import Iterator, Optional, Tuple

__all__ = ["lib"]

def _split_preload_var(val: str) -> list[str]:
    if not val:
        return []
    tokens = shlex.split(val)
    out: list[str] = []
    for t in tokens:
        out.extend(p for p in t.split(":") if p)
    return out

def _preload_env_name() -> str:
    return "DYLD_INSERT_LIBRARIES" if sys.platform == "darwin" else "LD_PRELOAD"

def _iter_preload_candidates() -> Iterator[str]:
    env_val = os.environ.get(_preload_env_name(), "")
    for cand in _split_preload_var(env_val):
        yield cand

def _try_dlopen(id_: str) -> Optional[CDLL]:
    try:
        # mode defaults to RTLD_LOCAL; that’s fine—we call through this handle.
        return CDLL(id_)
    except OSError:
        return None

def _exports_malloc_free(lib: CDLL) -> bool:
    try:
        _ = lib.malloc
        _ = lib.free
        return True
    except AttributeError:
        return False

def _configure_alloc_sigs(lib: CDLL) -> None:
    # Ensure correct prototypes (critical on 64-bit):
    #   void* malloc(size_t);  void free(void*);
    lib.malloc.argtypes = [c_size_t]
    lib.malloc.restype = c_void_p
    lib.free.argtypes = [c_void_p]
    lib.free.restype = None

def _process_default_lib() -> CDLL:
    """
    Return a handle that resolves symbols from the process global namespace:
    the exact libc/libSystem Python is already using.
    """
    return CDLL(None)

@cache
def lib() -> Tuple[CDLL, str, str]:
    """
    Returns (lib_handle, identifier, source) where source is 'preload' or 'process'.
    """
    # 1) Honor preloaded libraries in order
    for cand in _iter_preload_candidates():
        lib = _try_dlopen(cand)
        if lib and _exports_malloc_free(lib):
            _configure_alloc_sigs(lib)
            return lib, cand, "preload"

    # 2) Fall back to the process’s own libc (exactly what Python uses)
    lib = _process_default_lib()
    _configure_alloc_sigs(lib)
    return lib, "RTLD_DEFAULT", "process"
