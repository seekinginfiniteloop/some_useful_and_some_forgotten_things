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

"""
This is a very rough draft for a dictionary schema generator. The idea was to use a dict child class to generate a schema for a dictionary. I ended up not needing it for what I was working on, but I thought it was an interesting idea. I may come back to it at some point.

I know that pylance seems to do a pretty good job at doing this in vscode, but that's written in typescript, so it necessarily approaches it differently. All the same, next step was hunting down that code to see how it works.
"""
import typing

from array import array
from collections import (
    ChainMap,
    Counter,
    OrderedDict,
    UserDict,
    UserList,
    UserString,
    defaultdict,
    deque,
    namedtuple,
)
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import ParseResult, ParseResultBytes, urlparse
from uuid import UUID


class TypeDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = self._generate_schema(self)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.schema[key] = self._resolve_type(value)

    def _generate_schema(self, obj):
        match obj:
            case dict():
                return {k: self._generate_schema(v) for k, v in obj.items()}
            case [*_]:
                return self._resolve_sequences(obj)
            case str():
                return self._eval_string(obj)
            case bytes():
                return self._eval_string(obj, byt=True)
            case "__iter__":
                return self._resolve_sequences(obj)
            case _:
                return type(obj)

    def _eval_string(self, obj: str | bytes, byt=False) -> Any:
        if obj.isdigit():
            return bytes if byt else int
        elif obj.lower() in {"true", "false"} or obj.title() in {"True", "False"}:
            return bool
        elif self._is_uuid(obj, byt):
            return UUID
        elif self._is_path(obj, byt):
            return Path
        elif self._is_url(obj):
            return "URL" if isinstance(obj, str) else "URL[bytes]"
        return str if isinstance(obj, str) else bytes

    def _is_url(self, obj: str | bytes) -> bool:
        try:
            parsed: ParseResult | ParseResultBytes = urlparse(obj)
            return any([parsed.scheme, parsed.netloc])
        except Exception:
            return False

    def _is_path(self, obj: str | bytes, byt=False) -> bool:
        try:
            if byt:
                obj = obj.decode()
            p = Path(obj)
            if not p.exists():
                p.touch()
                p.unlink()
            return True
        except Exception:
            return False

    def _is_uuid(self, obj: str | bytes, byt=True) -> bool:
        try:
            if byt:
                UUID(bytes=obj)
                return True
            UUID(obj)
            return True
        except ValueError:
            return False

    def _resolve_sequences(self, obj: Iterable[Any]) -> Iterable[Any]:
        obj_type = type(obj)
        element_types = {type(item) for item in obj}
        if len(element_types) == 1:
            return obj_type[next(iter(element_types))]
        return obj_type[tuple(element_types)]

    def _resolve_type(self, value):
        return self._generate_schema(value)

    @property
    def builtins(self) -> tuple:
        return (
            callable,
            bool,
            memoryview,
            bytearray,
            bytes,
            complex,
            dict,
            float,
            frozenset,
            int,
            list,
            set,
            str,
            tuple,
            range,
        )

    @property
    def pytypes(self) -> set[Any]:
        builtins = set(self.builtins)
        t_types = {
            getattr(typing, t)
            for t in dir(typing)
            if t[0].isupper
            and not t.startswith("_")
            and t not in ["TYPE_CHECKING", "EXCLUDED_ATTRIBUTES"]
        }
        collection_types = {
            defaultdict,
            deque,
            namedtuple,
            OrderedDict,
            UserString,
            UserList,
            UserDict,
            Counter,
            ChainMap,
        }
        return builtins.update([t_types, collection_types, array])  # type:ignore # how would this ever return None pylance?
