"""AWS Lambda entry point.

Uses the ``mangum`` adapter to translate API Gateway / ALB events
into WSGI requests that Flask can handle.

Configure your Lambda handler as: ``lambda_handler.handler``
"""

from mangum import Mangum

from app import create_app
from app.utils.logging import setup_logging

setup_logging()

# Create the Flask app once (re-used across warm invocations)
flask_app = create_app()

# Mangum adapter: translates Lambda event → WSGI → Flask
handler = Mangum(flask_app, lifespan="off")
