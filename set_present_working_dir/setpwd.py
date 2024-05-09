#!/usr/bin/env /usr/bin/python
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

import contextlib
import os
import sys

from typing import Literal


def run_again():
    os.execve(os.path.realpath(__file__), sys.argv, os.environ)


def set_pwd():
    # Retrieve environment variables
    pwd = os.environ.get("pwd")
    other_pwd = os.environ.get("PWD")
    cwd = os.getcwd()

    # Determine the new working directory
    new_pwd = pwd or other_pwd or cwd

    new_pwd = pwd or other_pwd or cwd

    # Check if the new working directory is valid
    if not os.path.isdir(new_pwd):
        # Default to the user's home directory if necessary
        home = os.environ.get("HOME", f'/home/{os.environ.get("USER")}')
        with contextlib.chdir(home):
            # No operation needed inside the context manager
            pass
        new_pwd = home

    return new_pwd


def define_pwd(new_pwd, arg1, arg2) -> Literal[True]:
    os.environ[arg1] = new_pwd
    print(f"{arg2}{os.environ[arg1]}")
    return True


if __name__ == "__main__":
    main()


def main():
    new_pwd = set_pwd()

    if os.environ.get("was_run") != "1":
        os.environ["was_run"] = "1"
        run_again()
    # Update environment variables
    reset = False
    if os.environ.get("pwd") is None:
        reset = define_pwd(new_pwd, "pwd", "pwd_set: ")
    else:
        print(f"pwd: {os.environ['pwd']}")
    if os.environ.get("PWD") is None:
        reset = define_pwd(new_pwd, "PWD", "PWD_set: ")
    else:
        print(f"PWD: {os.environ['PWD']}")
    if os.environ.get("cwd") is None:
        reset = define_pwd(new_pwd, "cwd", "cwd_set: ")
    else:
        print(f"cwd: {os.environ['cwd']}")
    if reset:
        run_again()
