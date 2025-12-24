"""
Маршруты для статических файлов
"""

from flask import Blueprint, send_from_directory

static_bp = Blueprint("static", __name__)


@static_bp.route("/static/<path:filename>")
def serve_static(filename):
    """Отдача статических файлов"""
    return send_from_directory("../frontend", filename)


@static_bp.route("/css/<filename>")
def serve_css(filename):
    """Отдача CSS файлов"""
    return send_from_directory("../frontend/css", filename)
