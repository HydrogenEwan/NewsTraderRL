from flask import Flask, jsonify

from web.app.portfolio.routes import portfolio_bp
from web.app.ticker_detail.routes import ticker_detail_bp
from web.app.web_context import WebResponseException


def create_app():
    app = Flask(__name__)
    app.config.from_object('web.app.config.Config')

    @app.errorhandler(WebResponseException)
    def handle_web_response_exception(e: WebResponseException):
        return jsonify(e.response.to_dict()), 500

    app.register_blueprint(portfolio_bp, url_prefix="/api/portfolio")
    app.register_blueprint(ticker_detail_bp, url_prefix="/api/ticker")
    return app