from flask import Blueprint, jsonify

from web.app.dto.ticker_detail_response import TickerDetailResponse
from web.app.ticker_detail.services import get_ticker_detail
from web.app.web_context import web_response_context
from web.app.dto.web_response import WebResponse


ticker_detail_bp = Blueprint('ticker_detail', __name__)


@ticker_detail_bp.route('/<string:ticker>', methods=['GET'])
def index(ticker: str):
    with web_response_context():
        ticker_detail = get_ticker_detail(ticker)
        response = WebResponse(result=True, data=ticker_detail)
        return jsonify(response.to_dict()), 200