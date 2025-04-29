from contextlib import contextmanager
from web.app.dto.web_response import WebResponse


@contextmanager
def web_response_context():
    try:
        yield
    except Exception as e:
        response = WebResponse(result=False, error=str(e))
        raise WebResponseException(response)

class WebResponseException(Exception):
    def __init__(self, response: WebResponse):
        self.response = response
