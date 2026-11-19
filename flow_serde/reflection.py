import importlib


class TypeNotFoundError(LookupError):
    """Raised when a qualified name can't be resolved to a class."""


def find_type(qualified_name: str) -> type:
    """Resolve a ``"package.module:ClassName"`` string to the class it names.

    Nested classes are supported with a dotted path after the colon,
    e.g. ``"my.module:Outer.Inner"``.

    Raises:
        TypeNotFoundError: if the string is malformed, the module can't be
            imported, the attribute doesn't exist, or it isn't a class.
    """
    module_name, sep, attr_path = qualified_name.partition(":")
    if not sep or not module_name or not attr_path:
        raise TypeNotFoundError(
            f"Invalid qualified name {qualified_name!r}; expected 'module:ClassName'"
        )

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        # Only treat it as "not found" if the missing module is the one we asked
        # for (or one of its parents). A missing dependency *inside* the target
        # module is a real error and should propagate unchanged.
        if e.name is not None and (
            module_name == e.name or module_name.startswith(e.name + ".")
        ):
            raise TypeNotFoundError(
                f"Module {module_name!r} not found (resolving {qualified_name!r})"
            ) from e
        raise

    obj: object = module
    for part in attr_path.split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError as e:
            raise TypeNotFoundError(
                f"{part!r} not found while resolving {qualified_name!r}"
            ) from e

    if not isinstance(obj, type):
        raise TypeNotFoundError(
            f"{qualified_name!r} resolved to {type(obj).__name__}, not a class"
        )

    return obj
