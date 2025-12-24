"""
Тесты для модуля пагинации
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask import request as flask_request
from utils.pagination import get_pagination_params


def test_get_pagination_params_default():
    """Тест получения параметров пагинации по умолчанию"""
    app = Flask(__name__)
    with app.test_request_context("/api/test"):
        page, per_page = get_pagination_params(flask_request)
        assert page == 1
        assert per_page == 50  # DEFAULT_PAGE_SIZE


def test_get_pagination_params_custom():
    """Тест получения кастомных параметров пагинации"""
    app = Flask(__name__)
    with app.test_request_context("/api/test?page=3&per_page=25"):
        page, per_page = get_pagination_params(flask_request)
        assert page == 3
        assert per_page == 25


def test_get_pagination_params_max_limit():
    """Тест ограничения максимального размера страницы"""
    app = Flask(__name__)
    with app.test_request_context("/api/test?page=1&per_page=200"):
        page, per_page = get_pagination_params(flask_request)
        assert per_page == 100  # MAX_PAGE_SIZE


def test_get_pagination_params_min_values():
    """Тест минимальных значений"""
    app = Flask(__name__)
    with app.test_request_context("/api/test?page=0&per_page=-5"):
        page, per_page = get_pagination_params(flask_request)
        assert page == 1  # Минимум 1
        assert per_page == 1  # Минимум 1
