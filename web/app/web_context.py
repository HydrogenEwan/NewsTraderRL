import traceback
from contextlib import contextmanager
from web.app.dto.web_response import WebResponse


@contextmanager
def web_response_context():
    try:
        yield
    except Exception as e:
        tb_str = traceback.format_exc()

        response = WebResponse(
            result=False,
            error=str(e),
            traceback=tb_str
        )
        raise WebResponseException(response)

class WebResponseException(Exception):
    def __init__(self, response: WebResponse):
        self.response = response
