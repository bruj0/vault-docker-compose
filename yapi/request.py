import logging
from pprint import pprint
from box import Box
from builtins import str as ustr
from yapi.extensions import Extensions
import functools
import requests
from requests_toolbelt.utils import dump

logger = logging.getLogger(__name__)
# for k,v in  logging.Logger.manager.loggerDict.items()  :
#         print('+ [%s] {%s} ' % (str.ljust( k, 20)  , str(v.__class__)[8:-2]) ) 
#         if not isinstance(v, logging.PlaceHolder):
#             for h in v.handlers:
#                 print('     +++',str(h.__class__)[8:-2] )

class _FormattedString(object):
    """Wrapper class for things that have already been formatted

    This is only used below and should not be used outside this module
    """

    def __init(self, s):
        super(_FormattedString, self).__init__(s)

class request():
    variables = {}
    extensions = None
    request_args = {}

    def __init__(self,rspec,variables):
        self.variables = variables
        self.extensions = Extensions()

        logger.debug(f"Data passed to request: {rspec}")

        expected = {
            "method",
            "url",
            "headers",
            "data",
            "params",
            "auth",
            "json",
            "verify",
            "files",
            "stream",
            "timeout",
            "cookies",
            "cert",
            # "hooks",
            "follow_redirects",
        }

        check_expected_keys(expected, rspec)

        self.request_args = self.get_request_args(rspec)

    def run(self):
        with requests.Session() as session:
            ra = self.request_args

            req = requests.Request(ra['method'], ra['url'],json=ra['json'],headers=ra['headers'])
            prepped = req.prepare()
            response = session.send(prepped)
            data = dump.dump_all(response)
            logger.debug(f"Response={data.decode('utf-8')}")

    #TODO 
    #add test_block_config
    def get_request_args(self,rspec):

        request_args = {}

        # Ones that are required and are enforced to be present by the schema
        required_in_file = ["method", "url"]

        optional_in_file = [
            "json",
            "data",
            "params",
            "headers",
            "files",
            "timeout",
            "cert",
             "auth"
        ]
        optional_with_default = {"verify": True, "stream": False}
        #METHOD
        if "method" not in rspec:
                logger.debug("Using default GET method")
                rspec["method"] = "GET"

        #CONTENT
        content_keys = ["data", "json", "files"]

        in_request = [c for c in content_keys if c in rspec]
        if len(in_request) > 1:
            #If more than one content defined raise an exception
            if set(in_request) != {"data", "files"}:
                raise f"Can only specify one type of request data in HTTP request (tried to send {','.join(in_request)})"

        #HEADERS
        headers = rspec.get("headers", {})
        has_content_header = "content-type" in [h.lower() for h in headers.keys()]

        if "files" in rspec:
            if has_content_header:
                logger.warning(
                    "Tried to specify a content-type header while sending a file - this will be ignored"
                )
                rspec["headers"] = {
                    i: j for i, j in headers.items() if i.lower() != "content-type"
                }

        fspec = format_keys(rspec, self.variables)

        request_args=add_request_args(request_args,fspec,required_in_file, False)
        request_args=add_request_args(request_args,fspec,optional_in_file, True)

        logger.debug(f"Data after substitution: {fspec}")

        if "auth" in fspec:
            request_args["auth"] = tuple(fspec["auth"])

        if "cert" in fspec:
            if isinstance(fspec["cert"], list):
                request_args["cert"] = tuple(fspec["cert"])

        if "timeout" in fspec:
            # Needs to be a tuple, it being a list doesn't work
            if isinstance(fspec["timeout"], list):
                request_args["timeout"] = tuple(fspec["timeout"])

        logger.debug(f"request_args={request_args}")

        for key in optional_in_file:
            try:
                func = self.get_wrapped_create_function(request_args[key].pop("$ext"))
                logger.debug(f"Func is {func}")
            except (KeyError, TypeError, AttributeError):
                #logger.info(f"Testing func in {key}")
                pass
            else:
                request_args[key].update(func())
                logger.debug(f"request_args[key]={request_args[key]}")

        # If there's any nested json in parameters, urlencode it
        # if you pass nested json to 'params' then requests silently fails and just
        # passes the 'top level' key, ignoring all the nested json. I don't think
        # there's a standard way to do this, but urlencoding it seems sensible
        # eg https://openid.net/specs/openid-connect-core-1_0.html#ClaimsParameter
        # > ...represented in an OAuth 2.0 request as UTF-8 encoded JSON (which ends
        # > up being form-urlencoded when passed as an OAuth parameter)
        for key, value in request_args.get("params", {}).items():
            if isinstance(value, dict):
                request_args["params"][key] = quote_plus(json.dumps(value))

        for key, val in optional_with_default.items():
            request_args[key] = fspec.get(key, val)        

        # TODO
        # requests takes all of these - we need to parse the input to get them
        # "cookies",

        # These verbs _can_ send a body but the body _should_ be ignored according
        # to the specs - some info here:
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
        if request_args["method"] in ["GET", "HEAD", "OPTIONS"]:
            if any(i in request_args for i in ["json", "data"]):
                logger.warn(
                    "You are trying to send a body with a HTTP verb that has no semantic use for it"
                )
        logger.debug(f"request_args={request_args}")
        return request_args


    def get_wrapped_create_function(self,ext):
        """Same as above, but don't require a response
        """
        logger.debug(f"ext={ext}")
        args = ext.get("extra_args") or ()
        kwargs = ext.get("extra_kwargs") or {}

        try:
            class_name, funcname = ext["function"].split(".")
        except ValueError as e:
            msg = f"Expected entrypoint in the form class.function: {e}"
            logger.exception(msg)

        try:
            func = self.extensions.call_method(funcname)
        except AttributeError as e:
            msg = f"No function named {funcname} in {class_name} \n {e}"
            logger.exception(msg)

        #func = import_ext_function(ext["function"])
        logger.debug(f"Adding function {func} with args:{args} and kwargs:{kwargs}")
        @functools.wraps(func)
        def inner():
            return func(*args, **kwargs)

        inner.func = func

        return inner

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
        logger.error(msg)
        raise exceptions.UnexpectedKeysError(msg)

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
    #pprint(box_vars)

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