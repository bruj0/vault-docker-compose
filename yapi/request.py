import logging
from pprint import pprint
from box import Box
from builtins import str as ustr


logger = logging.getLogger(__name__)


class _FormattedString(object):
    """Wrapper class for things that have already been formatted

    This is only used below and should not be used outside this module
    """

    def __init(self, s):
        super(_FormattedString, self).__init__(s)

class request():
    data = {}
    variables = {}

    def __init__(self,data,variables):
        logger.info(f"Data passed to request: {data}")
        self.data = data
        self.variables = variables

    def send(self):
        rspec = self.data

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

        fspec = self.format_keys(rspec, self.variables)

        logger.debug(fspec)

    def format_keys(self,val, variables, no_double_format=True):
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
                formatted[key] = self.format_keys(val[key], box_vars)
        elif isinstance(val, (list, tuple)):
            formatted = [self.format_keys(item, box_vars) for item in val]
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
