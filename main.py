from app import create_app
from app.utils import setup_logging


def main():
    setup_logging("DEBUG")
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
