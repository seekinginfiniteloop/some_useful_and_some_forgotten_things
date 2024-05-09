"""
MIT License

Copyright (c) 2023 Adam Poulemanos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re
from enum import Enum
from json import JSONDecodeError, dump, dumps, load, loads
from pathlib import Path
from sys import path
from typing import Any, Callable, Dict, List, Union

from attrs import define, field

@unique
class TidyErrorType(Enum):
    """
    An enumeration of error types that can occur in the TidyJSON module.

    Attributes
    ----------
        INVALID_CHARACTER: Represents an error where an invalid character is
        encountered.
        MISSING_BRACKET: Represents an error where a bracket is missing.
        MISSING_QUOTE: Represents an error where a quote is missing.
        UNEXPECTED_TOKEN: Represents an error where an unexpected token is
        encountered.
    """

    INVALID_CHARACTER = "Invalid Character"
    MISSING_BRACKET = "Missing Bracket"
    MISSING_QUOTE = "Missing Quote"
    UNEXPECTED_TOKEN = "Unexpected Token"

@define(slots=False, kw_only=True, auto_attribs=True, order=True)
class ErrorContext:
    """
    Represents the context of an error that occurred during JSON parsing.

    This class captures detailed information about the error, including the type of error,
    its position in the JSON string, and a snippet of the JSON string around the error for context.
    It's used by the `ErrorManager` class to provide comprehensive error details.

    Attributes
    ----------
    error_type : TidyErrorType
        The type of error encountered (e.g., invalid character, missing bracket, etc.).
    position : int
        The position in the JSON string where the error occurred.
    json_str : str
        The JSON string being parsed when the error was encountered.

    Methods
    -------
    __attrs_post_init__():
        Initializes the error context by extracting a snippet of the JSON string around the error position.
    """

    error_type: TidyErrorType
    position: int
    json_str: str

    def __attrs_post_init__(self) -> None:
        self.error_context = self.json_str[max(0, self.position - 10) : min(len(self.json_str), self.position + 10)]

@define(slots=False, kw_only=True, auto_attribs=True, order=True)
class ErrorManager(Exception):
    """
    Custom exception class for handling errors in JSON parsing.

    Extends the base Exception class and is used to manage errors specific to JSON parsing in TidyJSON.
    It provides a structured way to capture and report detailed error information, including the type
    of error, its position, and a context snippet from the JSON string.

    Attributes
    ----------
    context : ErrorContext
        An instance of `ErrorContext` containing detailed information about the error.

    Methods
    -------
    __str__():
        Overrides the default string representation to provide a detailed error message incorporating
        information from the `ErrorContext`.
    """

    context: ErrorContext

    def __str__(self):
        return f"{self.context.error_type.value} at position: {self.context.position} context: {self.context.error_context}"


def clean_json_string(json_str: str) -> str:
    """
    Cleans the JSON string by removing leading/trailing whitespaces and comments. Utility function for handling potential issues before parsing.

    Parameters
    ----------
    json_str : The JSON string to clean.

    Returns
    --------
    The cleaned JSON string.

    """
    json_str = re.sub(r"^\s+|\s+$", "", json_str)
    json_str = re.sub(r"/\*.*?\*/", "", json_str)
    return json_str.replace("\\n", " ").replace("\\r", " ").strip()


@define(kw_only=True, auto_attribs=True, order=True)
class TidyJSONParser:
    """
    This class is a refactoring with additional handling for nested JSON
    from work by Stefano Baccianella under the MIT license, (c) 2023. That
    work is itself based on work by Jos de Jong, under the ISC license, (c) 2020-2023. [json_repair](https://github.com/mangiucugna/json_repair) and [jsonrepair](https://github.com/josdejong/jsonrepair).

    A custom JSON parser class for handling complex JSON parsing scenarios
    and deeply nested structures, according to the following BNF definition:

    <json> ::= <primitive> | <container>

        <primitive> ::= <number> | <string> | <boolean>
        ; Where:
        ; <number> is a valid real number expressed in one of a number of given formats
        ; <string> is a string of valid characters enclosed in quotes
        ; <boolean> is one of the literal strings 'true', 'false', or 'null' (unquoted)

        <container> ::= <object> | <array>
        <array> ::= '[' [ <json> *(', ' <json>) ] ']' ; A sequence of JSON values separated by commas
        <object> ::= '{' [ <member> *(', ' <member>) ] '}' ; A sequence of 'members'
        <member> ::= <string> ': ' <json> ; A pair consisting of a name, and a JSON value

    It also seeks to identify and fix malformed JSON, especially
    problem characters. It supports iterative and recursive
    parsing approaches, selecting which to use based on the structure of the json, and includes custom error handling.


    Attributes
    ----------
    json_str: A string representing the JSON data to be parsed.

    index: An integer representing the current position in the JSON string
        during parsing.

    json_out: Stores the output after parsing the JSON string. This
        attribute is set after initialization.

    Methods
    -------

    parse: Main method for parsing the JSON string, delegating parsing
        based on the current character.

    get_parser_method: Returns a parsing method based on the current character.

    parse_object: Parses a JSON object and returns a dictionary.

    parse_array: Parses a JSON array and returns a list.

    parse_collection: A generalized method for parsing JSON collections like
        objects and arrays.

    expect_and_skip: Skips spaces and a specified character in the JSON
        string during parsing.

    parse_string: Parses a JSON string value.

    parse_number: Parses a JSON number and returns an int or float.

    parse_numeric_value : Parses an int/float from parse_number

    parse_boolean_or_null: Parses JSON literals 'true', 'false', and 'null'.

    get_next_char: Returns the current character in the JSON string at the parsing index, or None if the end is reached.

    skip_whitespace: Used to skip the index past whitespaces.

    """

    json_str: str
    index: int = field(default=0)
    json_out: Any = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """
        A post-initialization method.

        Initializes the parsing process and stores it in the attribute `json_out`.
        """
        self.json_str = clean_json_string(json_str=self.json_str)
        self.json_out = self.parse()

    def parse(self) -> Union[Dict[str, Any], List[Any], str, float, int, bool, None]:
        """
        Delegate parsing based on the current character in the JSON string.

        This method serves as a dispatcher to various parsing functions
        depending on the character at the current
        parsing position. It handles objects, arrays, strings, numbers, and
        boolean/null literals.

        Returns
        -------
        The parsed Python object corresponding to the current segment of the
        JSON string.

        Raises
        ------
        ErrorManager
            If an unexpected token is encountered during parsing.
        """
        self.skip_whitespace()
        char: str | bool = self.get_next_char()
        method = self.get_parser_method(char)
        parser_methods: Any = {
            "{": self.parse_object,
            "[": self.parse_array,
            '"': self.parse_string,
            "t": self.parse_boolean_or_null,
            "f": self.parse_boolean_or_null,
            "n": self.parse_boolean_or_null,
        }
        method: Any = parser_methods.get(
            char, self.parse_number if char.isdigit() or char == "-" else None
        )
        if method:
            return method()
        else:
            raise ErrorManager(
                error_type=TidyErrorType.UNEXPECTED_TOKEN,
                position=self.index,
                json_str=self.json_str,
            )

    def get_parser_method(self, char: str) -> Callable[[], Dict[str, Any]] | Callable[[], List[Any]] | Callable[[], str] | Callable[[], bool | None] | Callable[[], float | int] | None:
        """
        Selects parser method based on character input.

        Parameters
        ----------
        char: str for character to select parser method for.

        Returns
        -------
        The parser method corresponding to the character input.

        Returns
        -------
        The parser method corresponding to the character input.

        """
        parser_methods = {
        '{': self.parse_object,
        '[': self.parse_array,
        '"': self.parse_string,
        't': self.parse_boolean_or_null,
        'f': self.parse_boolean_or_null,
        'n': self.parse_boolean_or_null
    }

        return parser_methods.get(char, self.parse_number if char.isdigit() or char == "-" else None)

    def parse_object(self) -> Dict[str, Any]:
        """
        Parse an object in the JSON string and return a dictionary.

        This method is responsible for parsing JSON objects (delimited by
        curly braces {}) and converting them into Python dictionaries.

        Returns
        -------
        A dictionary representing the parsed JSON object.
        """
        return self.parse_collection(
            end_char="}", parse_func=self.parse_string, delimiter=":"
        )

    def parse_array(self) -> List[Any]:
        """
        Parse an array in the JSON string and return a list.

        This method is responsible for parsing JSON arrays (delimited by
        square brackets []) and converting them into Python lists.

        Returns
        -------
        A list representing the parsed JSON array.
        """
        return self.parse_collection(end_char="]", parse_func=self.parse, delimiter=",")

    def parse_collection(
        self, end_char: str, parse_func: Callable, delimiter: str
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Generalized method for parsing JSON collections (objects and arrays).

        This method provides a unified approach to parse both JSON objects and
        arrays. It handles the parsing logic, including delimiters and end
        characters, and delegates the parsing of individual elements to a
        specified function.

        Parameters
        ----------
        end_char : The character that signifies the end of the collection.

        parse_func : The function to call for parsing individual elements of
        the collection.

        delimiter : The character that separates elements in the collection.

        Returns
        -------
        The parsed collection, either a dictionary (for objects) or a list
        (for arrays).
        """
        self.index += 1  # Skip start character ('{' or '[')
        collection = {} if end_char == '}' else []
        while (char := self.get_next_char()) != end_char:
            if isinstance(collection, dict):
                key = parse_func()
                self.expect_and_skip(delimiter)
                collection[key] = self.parse()
            else:
                collection.append(parse_func())
            self.skip_whitespace()
            if self.get_next_char() == ',':
                self.index += 1
                self.skip_whitespace()
        self.index += 1  # Skip end character ('}' or ']')
        return collection

    def expect_and_skip(self, expected_char: str) -> None:
        """
        Expect a specific character and skip it, otherwise raise an error.

        """
        if self.get_next_char() != expected_char:
            raise ValueError(f"Expected '{expected_char}' at index {self.index}")
        self.index += 1

    def parse_string(self) -> str:
        """
        Parses a JSON string value.

        This method extracts a string value from the JSON string, handling the
        escape characters and quotes that define the boundaries of a JSON
        string.

        Returns
        -------
        The extracted string value from the JSON data.
        """
        self.index += 1  # Skip opening quote
        start: int = self.index
        while (char := self.get_next_char()) != '"':
            if char is False:
                raise ValueError(f"Unterminated string starting at index {start}")
            self.index += 1
        self.index += 1  # Skip closing quote
        return self.json_str[start : self.index - 1]


    def parse_number(self) -> Union[float, int]:
        """
        Parses a JSON number and returns it as an int or float.

        This method parses numeric values in the JSON string, distinguishing
        between integers and floating-point numbers based on the presence of a
        decimal point.

        Returns
        -------
        The parsed number, returned as a float if it contains a decimal point,
        otherwise as an int.
        """
        start = self.index
        while (char := self.get_next_char()) and char in "0123456789-.eE":
            self.index += 1
        number_str = self.json_str[start : self.index]
        return self.parse_numeric_value(number_str, start)

    def parse_numeric_value(self, number_str: str, start: int) -> Union[float, int]:
        """

        Parses a numeric value from a string, handling int and float types.

        """
        try:
            return float(number_str) if '.' in number_str or 'e' in number_str or 'E' in number_str else int(number_str)
        except ValueError as e:
            raise ValueError(f"Invalid number format at index {start}") from e


    def parse_boolean_or_null(self) -> Union[bool, None]:
        """
        Parses JSON literals 'true', 'false', and 'null'.

        This method recognizes and converts the JSON literals 'true', 'false',
        and 'null' into their corresponding Python
        values: True, False, and None.

        Returns
        -------
        The boolean value True or False, or None, corresponding to the parsed JSON literal.

        Raises
        ------
        ErrorManager
            If the literal is not recognized as 'true', 'false', or 'null'.
        """
        literals = {
            'true': (True, 4),
            'false': (False, 5),
            'null': (None, 4)
        }
        for literal, (value, length) in literals.items():
            if self.json_str.startswith(literal, self.index):
                self.index += length
                return value

        raise ErrorManager(
            error_type=TidyErrorType.UNEXPECTED_TOKEN,
            position=self.index,
            json_str=self.json_str
        )


    def get_next_char(self) -> Union[str, bool]:
        """
        Returns the current character in the JSON string at the parsing index.

        This method provides the character at the current index of the JSON
        string. If the index is beyond the end of the string, it returns None.

        Returns
        -------
        The character at the current parsing index, or None if the end of the
        string is reached.
        """

        return self.json_str[self.index] if self.index < len(self.json_str) else False


    def skip_whitespace(self) -> None:
        """
        Skips over spaces in the JSON string during parsing.

        This method advances the parsing index past any spaces; used to skip over delimiters and whitespace in the JSON string.

        Parameters
        ----------
        char : The character to skip along with any spaces.
        """
        while self.index < len(self.json_str) and self.json_str[self.index].isspace():
            self.index += 1

@define(kw_only=True, auto_attribs=True, order=True)
class TidyJSON:
    """
    Primary API entrypoint for TidyJSON. You can access all functionality from
    this class, which acts as a master/controller class. TidyJSON supports
    string input either was a string/stream or from a file, and will
    automatically detect and shift approaches based on whether you provide a
    path-like string or a string directly. You may also provide a save
    location to save to a file when you are done.

    Most of the heavy lifting is done by the TidyJSONParser class, which is a
    subclass of Python's JSONDecoder class. This class handles the parsing of
    the JSON string and provides the parsed JSON data to the TidyJSON class.

    To decode and parse JSON, which is TidyJSON's primary function:

    Examples
    --------
    Encoding a string:
    ```python
    from TidyJSON import TidyJSON

    tidy = TidyJSON(json_input=my_json_string)
    decoded_string = tidy.decode
    ```

    Encoding a file, and saving to a file (note, strings will be automatically
    converted to Path objects):
    ```python
    from TidyJSON import TidyJSON

    my_json_file = "/path/to/my/json/file.json"

    my_new_encoded_save_location = "/path/to/my/new/save/location.json"

    tidy = TidyJSON(json_input=my_json_file,
    save_path=my_new_encoded_save_location)

    decoded_json_file = tidy.decode

    my_newly_encoded_file = tidy.encode
    ```

    Similarly, if you want to decode a file, and pipe the decoded stream to
    something else, you would just not pass a save_path (see below).

    You can always access the decoded and parsed JSON with the `json`
    attribute:

    ```python
    from TidyJSON import TidyJSON

    def foo(decoded_json):
        #do something with the decoded json
        pass

    def bar(encoded_json):
        #do something with the encoded json
        pass

    decoder = tidy.decode
    my_decoded_json = tidy.json
    encoder = tidy.encode

    #we could also use decoder here; .decode returns the json attribute
    foo_output = foo(my_decoded_json)
    bar_output = bar(encoder)
    ```

    Attributes
    ----------
    json_input: A string representing the path to the JSON file or the
        JSON data itself. This attribute is set only if JSON data is
        provided during initialization. If it isn't... well, you're not
        going to be able to do anything useful.

    json: Stores the parsed JSON data. This attribute is set after
        decoding the JSON input, and will be None until you use .decode.

    save_path: A string representing the path where the JSON data will be
        saved. This attribute is set only if a save path is provided.

    Methods
    -------

    decode: A property that decodes the JSON input into Python data
        structures and populates the `json` attribute.

    encode: A property that encodes the Python data structures back into a JSON formatted string or saves it to a file if `save_path` is provided.


    Notes
    -----
    The class uses properties for encoding and decoding to provide a simple
    and intuitive interface.

    The `_load_file`, `_load_string`, and `_check_for_file` methods are
    private utility methods:

    *Private Methods*:
        _load_file: Loads JSON data from a file specified in `json_input`.
        _load_string: Loads JSON data from a string in `json_input`.
        _check_for_file: Checks if `json_input` is a valid file path.
    """

    json_input: str = field(default=None, init=False)
    json: Any = field(default=None, init=False)
    save_path: str = field(default=None, init=False)

    @property
    def decode(self) -> Any:
        """
        Decodes the JSON input into Python data structures.

        This property method handles the decoding of JSON data. If
        `json_input` is a file path, it loads the JSON from the file. If it's a JSON string, it decodes the string directly.

        Returns
        -------
        The Python representation of the decoded JSON data.

        Raises
        ------
        ValueError
            If no JSON input is provided or if the input is not a valid JSON string or file path.
        """
        if isinstance(self.json_input, Path):
            try:
                with open(file=Path(self.json_input), mode="r") as f:
                    self.json = load(fp=f, cls=TidyJSONParser)
                    return self.json
            except JSONDecodeError:
        elif isinstance(self.json_input, str):
            try:
                self.json = loads(s=self.json_input, cls=TidyJSONParser)
                return self.json
            except JSONDecodeError:

    @property
    def encode(self) -> Union[None, str]:
        """

        Encodes Python data structures back into a JSON formatted string or
        saves it to a file.

        This property method handles the encoding of Python data structures to
        JSON. If a `save_path` is provided, it saves the JSON data to the
        specified file. Otherwise, it returns the JSON data as a string.

        Returns
        -------
        The JSON formatted string if no `save_path` is provided, otherwise None.

        Raises
        ------
        ValueError
            If there is no JSON data to encode.
        """

        if self.save_path:
            with open(file=self.save_path, mode="w") as f:
                dump(obj=self.json, fp=f, indent=4, strict=False)
        elif self.json:
            return dumps(strict=False)
        else:
            raise ValueError(
                "TidyJSON object has no data to encode in the instance json  attribute. Please pass data next time."
            )

    def _load_file(self) -> Any:
        """
        Loads JSON data from a file specified in `json_input`.

        This internal method reads a JSON file specified by the `json_input` path and parses it using the
        custom `TidyJSONParser`.

        Returns
        -------
        The Python representation of the loaded JSON data.
        """
        try:
            with open(file=Path(self.json_input), mode="r") as f:
                return load(fp=f, cls=TidyJSONParser)
        except JSONDecodeError:

    def _load_string(self) -> None:
        """
        Loads JSON data from a string in `json_input`.

        This internal method parses a JSON string provided in `json_input`
        using the custom `TidyJSONParser`.

        Returns
        -------
        The method does not return a value but updates the `json` attribute of
        the instance.
        """
        return loads(s=self.json_input, cls=TidyJSONParser)

    def _check_for_file(self) -> bool:
        """
        Checks if `json_input` is a valid file path.

        This internal method verifies whether the provided `json_input` is a
        path to an existing file.

        Returns
        -------
        True if `json_input` is a valid file path, False otherwise.
        """
        return Path(self.json_input).is_file()
