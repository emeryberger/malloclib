import mallocfinder

def main() -> None:
    lib, ident, source = mallocfinder.lib()
    print(f"{lib=} {ident=} {source=}")
    p = lib.malloc(24)
    print(f"allocated: {hex(p)} {p!r} via {ident} (source={source})")
    lib.free(p)

if __name__ == "__main__":
    main()
