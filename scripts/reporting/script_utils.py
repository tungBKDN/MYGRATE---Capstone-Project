#!/usr/bin/env python3
import re


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_ansi(text):
    return ANSI_ESCAPE.sub("", text)
