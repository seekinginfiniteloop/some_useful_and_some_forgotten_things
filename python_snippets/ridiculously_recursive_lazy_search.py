"""
 Copyright 2024 Adam Poulemanos

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """

# I don't remember why I made this... but I do remember I didn't actually need it. As I worked through the problem, I found a better way.
# If you ever need something that's ridiculously recursive and lazy; here's a good starting point.

from typing import Any, Generator


def name_item(item) -> str:  # sourcery skip: assign-if-exp, reintroduce-else
    """Helper function to get the name of an item/object"""
    if hasattr(item, "__name__"):
        return item.__name__
    return str(item)


def ridiculously_recursive_lazy_search(
    data: Any, search_obj: Any, path: str = "", stringify_search: bool = True
) -> Generator[tuple[str, Any], None, None]:
    """
    Searches for a given object within nested data structures, yielding paths and matching objects.

    TODO: Add ability to inject a custom callable to define a match

    Args:
        data: The data structure to search within.
        search_obj: The object to search for within the data structure. Accepts recursive objects, and will iterate over them.
        path: The current path within the data structure (default is an empty string).
        stringify_search: Whether to search for both the object, and if it's not a string, to also search for a string representation of the object (default is True).

    Yields:
        tuple[str, Any]: A tuple containing the dot notation path and the matching object found.

    Examples:
        >>> data = {"a": {"b": "c"}}
        >>> search_obj = "c"
        >>> for path, obj in ridiculously_recursive_lazy_search(data, search_obj):
        ...     print(f"Found at path: {path}, object: {obj}")
    """

    if search_obj is data or search_obj == data:
        yield path, data
    if not data:
        return

    search_str = search_obj if isinstance(search_obj, str) else name_item(search_obj)
    search_obj = (
        search_obj
        if isinstance(search_obj, str)
        else ((search_obj, search_str) if stringify_search else search_obj)
    )
    data = bytes(data) if isinstance(data, (bytearray, memoryview)) else data
    search_obj = (
        bytes(search_obj)
        if isinstance(search_obj, (bytearray, memoryview))
        else search_obj
    )

    new_path = f"{path}.{name_item(data)}".strip(".")
    if hasattr(data, "__contains__") and search_obj in data:
        yield new_path, data

    container_attrs = ("__iter__", "__next__", "__contains__")
    if any(hasattr(search_obj, attr) for attr in container_attrs):
        for item in data:
            item_path = f"{new_path}.{name_item(item)}".strip(".")
            yield from ridiculously_recursive_lazy_search(
                data, item, path=item_path, stringify_search=stringify_search
            )

    if any(hasattr(data, attr) for attr in container_attrs):
        for item in data:
            item_path = f"{new_path}.{name_item(item)}".strip(".")
            yield from ridiculously_recursive_lazy_search(
                item, search_obj, path=item_path, stringify_search=stringify_search
            )
    elif data_items := getattr(data, "__dict__", {}):
        yield from ridiculously_recursive_lazy_search(
            data_items, search_obj, path=new_path, stringify_search=stringify_search
        )

    yield from ridiculously_recursive_lazy_search(
        data, search_str, path=new_path, stringify_search=stringify_search
    )
