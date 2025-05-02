from flask import Blueprint, jsonify, request

from web.app.dto.portfolio_response import PortfolioResponse
from web.app.portfolio.services import get_portfolio
from web.app.web_context import web_response_context
from web.app.dto.web_response import WebResponse


portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/', methods=['GET'], strict_slashes=False)
def index():
    with web_response_context():
        date_str = request.args.get('date')

        if date_str:
            try:
                from datetime import datetime
                datetime.strptime(date_str, "%Y-%m-%d")
                date = date_str
            except ValueError:
                date = None
        else:
            date = None

        portfolio = get_portfolio(date)
        portfolio_response = PortfolioResponse(portfolio)
        response = WebResponse(result=True, data=portfolio_response)
        return jsonify(response.to_dict()), 200