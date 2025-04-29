import click
from web.app.initialize import create_app

@click.group()
def cli():
    """Main CLI Entry Point"""
    pass

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to run the web server on')
@click.option('--port', default=5000, help='Port to run the web server on')
@click.option('--debug', is_flag=True, help='Run Flask in debug mode')
def run(host, port, debug):
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    cli()
