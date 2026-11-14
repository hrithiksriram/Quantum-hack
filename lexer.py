
import re


TOKEN_PATTERN = re.compile(
    r"""
    //.*?$                         | # Single-line comments
    /\*.*?\*/                      | # Multi-line comments
    "(?:\\.|[^"\\])*"              | # Strings
    ->                              | # Arrow
    \d+\.\d+|\d+                   | # Numbers
    [A-Za-z_][A-Za-z0-9_]*         | # Identifiers
    [^\s]                            # Other symbols
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL
)


def tokenize(source):
    tokens = TOKEN_PATTERN.findall(source)

    # Remove comments
    tokens = [
        token for token in tokens
        if not token.startswith("//")
        and not token.startswith("/*")
    ]

    return tokens
