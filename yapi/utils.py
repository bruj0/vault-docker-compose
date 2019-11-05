import logging
from box import Box
from builtins import str as ustr
import functools

logger = logging.getLogger(__name__)

class _FormattedString(object):
    """Wrapper class for things that have already been formatted

    This is only used below and should not be used outside this module
    """

    def __init(self, s):
        super(_FormattedString, self).__init__(s)

def check_expected_keys(expected, actual):
    """Check that a set of expected keys is a superset of the actual keys

    Args:
        expected (list, set, dict): keys we expect
        actual (list, set, dict): keys we have got from the input

    Raises:
        UnexpectedKeysError: If not actual <= expected
    """
    expected = set(expected)
    keyset = set(actual)

    if not keyset <= expected:
        unexpected = keyset - expected

        logger.debug("Valid keys = %s, actual keys = %s", expected, keyset)

        msg = "Unexpected keys {}".format(unexpected)
        logger.exception(msg)

def format_keys(val, variables, no_double_format=True):
    """recursively format a dictionary with the given values

    Args:
        val (object): Input dictionary to format
        variables (dict): Dictionary of keys to format it with
        no_double_format (bool): Whether to use the 'inner formatted string' class to avoid double formatting
            This is required if passing something via pytest-xdist, such as markers:
            https://github.com/taverntesting/tavern/issues/431

    Returns:
        dict: recursively formatted dictionary
    """
    formatted = val
    box_vars = Box(variables)

    if isinstance(val, dict):
        formatted = {}
        # formatted = {key: format_keys(val[key], box_vars) for key in val}
        for key in val:
            formatted[key] = format_keys(val[key], box_vars)
    elif isinstance(val, (list, tuple)):
        formatted = [format_keys(item, box_vars) for item in val]
    elif isinstance(formatted, _FormattedString):
        logger.debug("Already formatted %s, not double-formatting", formatted)
    elif isinstance(val, (ustr, str)):
        try:
            formatted = val.format(**box_vars)
        except KeyError as e:
            if val.startswith("{ext."):
                pass
            else:
                logger.error(
                    "Failed to resolve string [%s] with variables [%s]", val, box_vars
                )
                logger.error(f"Key(s) not found in format: {e}")
        except IndexError as e:
            logger.error(f"Empty format values are invalid {e}")
    else:
        logger.debug(f"Not formatting something of type: {type(formatted)}")

    return formatted

def add_request_args(request_args,fspec,keys, optional):
    for key in keys:
        try:
            request_args[key] = fspec[key]
        except KeyError:
            if optional or (key in request_args):
                continue

            # This should never happen
            raise
    return request_args

def quote(string, safe='/', encoding=None, errors=None):
    """quote('abc def') -> 'abc%20def'

    Each part of a URL, e.g. the path info, the query, etc., has a
    different set of reserved characters that must be quoted. The
    quote function offers a cautious (not minimal) way to quote a
    string for most of these parts.

    RFC 3986 Uniform Resource Identifier (URI): Generic Syntax lists
    the following (un)reserved characters.

    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
    reserved      = gen-delims / sub-delims
    gen-delims    = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
                / "*" / "+" / "," / ";" / "="

    Each of the reserved characters is reserved in some component of a URL,
    but not necessarily in all of them.

    The quote function %-escapes all characters that are neither in the
    unreserved chars ("always safe") nor the additional chars set via the
    safe arg.

    The default for the safe arg is '/'. The character is reserved, but in
    typical usage the quote function is being called on a path where the
    existing slash characters are to be preserved.

    Python 3.7 updates from using RFC 2396 to RFC 3986 to quote URL strings.
    Now, "~" is included in the set of unreserved characters.

    string and safe may be either str or bytes objects. encoding and errors
    must not be specified if string is a bytes object.

    The optional encoding and errors parameters specify how to deal with
    non-ASCII characters, as accepted by the str.encode method.
    By default, encoding='utf-8' (characters are encoded with UTF-8), and
    errors='strict' (unsupported characters raise a UnicodeEncodeError).
    """
    if isinstance(string, str):
        if not string:
            return string
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        string = string.encode(encoding, errors)
    else:
        if encoding is not None:
            raise TypeError("quote() doesn't support 'encoding' for bytes")
        if errors is not None:
            raise TypeError("quote() doesn't support 'errors' for bytes")
    return quote_from_bytes(string, safe)

def quote_plus(string, safe='', encoding=None, errors=None):
    """Like quote(), but also replace ' ' with '+', as required for quoting
    HTML form values. Plus signs in the original string are escaped unless
    they are included in safe. It also does not have safe default to '/'.
    """
    # Check if ' ' in string, where string may either be a str or bytes.  If
    # there are no spaces, the regular quote will produce the right answer.
    if ((isinstance(string, str) and ' ' not in string) or
        (isinstance(string, bytes) and b' ' not in string)):
        return quote(string, safe, encoding, errors)
    if isinstance(safe, str):
        space = ' '
    else:
        space = b' '
    string = quote(string, safe + space, encoding, errors)
    return string.replace(' ', '+')

def quote_from_bytes(bs, safe='/'):
    """Like quote(), but accepts a bytes object rather than a str, and does
    not perform string-to-bytes encoding.  It always returns an ASCII string.
    quote_from_bytes(b'abc def\x3f') -> 'abc%20def%3f'
    """
    if not isinstance(bs, (bytes, bytearray)):
        raise TypeError("quote_from_bytes() expected bytes")
    if not bs:
        return ''
    if isinstance(safe, str):
        # Normalize 'safe' by converting to bytes and removing non-ASCII chars
        safe = safe.encode('ascii', 'ignore')
    else:
        safe = bytes([c for c in safe if c < 128])
    if not bs.rstrip(_ALWAYS_SAFE_BYTES + safe):
        return bs.decode()
    try:
        quoter = _safe_quoters[safe]
    except KeyError:
        _safe_quoters[safe] = quoter = Quoter(safe).__getitem__
    return ''.join([quoter(char) for char in bs])