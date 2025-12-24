"""
Messenger Service - работа с чатами и сообщениями Avito
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("app")


class MessengerService:
    """Сервис для работы с Avito Messenger API"""

    def __init__(self, db_connection, avito_api):
        self.conn = db_connection
        self.api = avito_api

    @staticmethod
    def extract_text_from_message(msg_data: any) -> str:
        """Извлечь текст из любой структуры сообщения"""
        if not msg_data:
            return ""

        if isinstance(msg_data, str):
            return msg_data

        if not isinstance(msg_data, dict):
            return str(msg_data)

        # Пробуем разные ключи
        if msg_data.get("text"):
            return str(msg_data["text"])

        content = msg_data.get("content", {})
        if isinstance(content, dict):
            text = content.get("text", content.get("message", ""))
            if text:
                return str(text)
        elif content:
            return str(content)

        message = msg_data.get("message", {})
        if isinstance(message, dict):
            text = message.get("text", message.get("content", ""))
            if text:
                return str(text)
        elif message:
            return str(message)

        return ""

    @staticmethod
    def clean_json_message(msg: str) -> str:
        """Очистить сообщение от JSON-формата"""
        if not msg:
            return ""

        msg_str = str(msg).strip()

        # Если обычный текст, возвращаем как есть
        if (
            not msg_str.startswith("{")
            and not msg_str.startswith("'")
            and "'text'" not in msg_str
            and '"text"' not in msg_str
        ):
            return msg_str

        # Пробуем извлечь текст через regex
        patterns = [
            r"['\"]text['\"]\s*:\s*['\"]([^'\"]*)['\"]",
            r'"text"\s*:\s*"([^"]*)"',
            r"text\s*[:=]\s*['\"]([^'\"]*)['\"]",
            r"\{[^}]*text['\"]?\s*[:=]\s*['\"]([^'\"]*?)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, msg_str)
            if match and match.group(1) is not None:
                return match.group(1)

        return msg_str

    def get_chats_list(
        self,
        shop_id: Optional[int] = None,
        manager_id: Optional[int] = None,
        pool_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        with_total: bool = False,
    ) -> List[Dict]:
        """
        Получить список чатов с фильтрацией

        Args:
            shop_id: ID магазина (опционально)
            manager_id: ID менеджера (опционально)
            pool_only: Только чаты из пула

        Returns:
            List[Dict] | Tuple[List[Dict], int]: Список чатов и, при необходимости, общее количество
        """
        safe_limit = max(1, min(int(limit or 0), 500))
        safe_offset = max(0, int(offset or 0))

        # Проверяем, существуют ли колонки first_name и last_name
        has_name_columns = False
        try:
            cursor = self.conn.execute("PRAGMA table_info(users)")
            columns_info = cursor.fetchall()
            # PRAGMA table_info возвращает кортежи: (cid, name, type, notnull, dflt_value, pk)
            user_columns = [row[1] if len(row) > 1 else str(row[0]) for row in columns_info]
            has_name_columns = "first_name" in user_columns and "last_name" in user_columns
        except Exception:
            has_name_columns = False

        base_query = """
            FROM avito_chats c
            LEFT JOIN avito_shops s ON c.shop_id = s.id
            LEFT JOIN users u ON c.assigned_manager_id = u.id
            WHERE c.status != 'completed'
        """
        conditions = []
        params: List = []

        if shop_id:
            conditions.append("c.shop_id = ?")
            params.append(shop_id)

        # Убраны фильтры по менеджерам - все видят все чаты
        # if manager_id:
        #     conditions.append('c.assigned_manager_id = ?')
        #     params.append(manager_id)

        if pool_only:
            conditions.append("c.assigned_manager_id IS NULL")

        where_clause = ""
        if conditions:
            where_clause = " AND " + " AND ".join(conditions)

        total = None
        if with_total:
            total = self.conn.execute(
                f"""
                SELECT COUNT(*) as count
                {base_query}
                {where_clause}
            """,
                tuple(params),
            ).fetchone()["count"]

        # Используем разные запросы в зависимости от наличия колонок
        if has_name_columns:
            query = f"""
                SELECT 
                    c.*, 
                    s.name as shop_name, 
                    s.is_active as shop_active,
                    s.client_id, s.client_secret, s.user_id, s.webhook_registered,
                    COALESCE(
                        NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''),
                        u.username,
                        ''
                    ) as assigned_manager_name
                {base_query}
                {where_clause}
                ORDER BY 
                    CASE WHEN c.response_timer > 0 THEN 0 ELSE 1 END,
                    c.response_timer DESC,
                    c.updated_at DESC
                LIMIT ? OFFSET ?
            """
        else:
            query = f"""
                SELECT 
                    c.*, 
                    s.name as shop_name, 
                    s.is_active as shop_active,
                    s.client_id, s.client_secret, s.user_id, s.webhook_registered,
                    COALESCE(u.username, '') as assigned_manager_name
                {base_query}
                {where_clause}
                ORDER BY 
                    CASE WHEN c.response_timer > 0 THEN 0 ELSE 1 END,
                    c.response_timer DESC,
                    c.updated_at DESC
                LIMIT ? OFFSET ?
            """

        params_with_limits = params + [safe_limit, safe_offset]
        chats = self.conn.execute(query, tuple(params_with_limits)).fetchall()

        # Очищаем last_message и добавляем статусы
        chats_list = []
        chats_with_product_url = 0
        for chat in chats:
            chat_dict = dict(chat)
            chat_dict["last_message"] = self.clean_json_message(chat_dict.get("last_message", ""))

            # Проверяем наличие product_url в БД
            product_url_from_db = chat_dict.get("product_url")
            if product_url_from_db:
                chats_with_product_url += 1
                if chats_with_product_url <= 3:  # Логируем только первые 3 для диагностики
                    logger.info(
                        f"[GET CHATS LIST] Чат {chat_dict.get('id')}: product_url найден в БД = {product_url_from_db}"
                    )

            client_id = chat_dict.pop("client_id", None)
            client_secret = chat_dict.pop("client_secret", None)
            avito_user_id = chat_dict.pop("user_id", None)
            webhook_registered = bool(chat_dict.pop("webhook_registered", False))
            has_creds = bool(client_id and client_secret and avito_user_id)
            chat_dict["avito_credentials_status"] = "ok" if has_creds else "missing"
            chat_dict["has_avito_creds"] = has_creds
            chat_dict["webhook_registered"] = webhook_registered

            chats_list.append(chat_dict)

        logger.info(f"[GET CHATS LIST] Всего чатов: {len(chats_list)}, с product_url: {chats_with_product_url}")

        if with_total:
            return chats_list, (total or len(chats_list))
        return chats_list

    def get_chat_messages(self, chat_id: int, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Получить сообщения чата

        Args:
            chat_id: ID чата в БД
            limit: Количество сообщений
            offset: Смещение

        Returns:
            Tuple[List[Dict], int]: (список сообщений, общее количество)
        """
        safe_limit = max(1, min(int(limit or 0), 500))
        safe_offset = max(0, int(offset or 0))

        logger.info(f"[GET MESSAGES] Загружаем сообщения для чата {chat_id}, limit={safe_limit}, offset={safe_offset}")

        # Проверяем, существуют ли колонки first_name и last_name
        has_name_columns = False
        try:
            cursor = self.conn.execute("PRAGMA table_info(users)")
            columns_info = cursor.fetchall()
            # PRAGMA table_info возвращает кортежи: (cid, name, type, notnull, dflt_value, pk)
            user_columns = [row[1] if len(row) > 1 else str(row[0]) for row in columns_info]
            has_name_columns = "first_name" in user_columns and "last_name" in user_columns
        except Exception:
            has_name_columns = False

        # Получаем сообщения из БД
        if has_name_columns:
            messages = self.conn.execute(
                """
                SELECT m.*, 
                       COALESCE(
                           NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''),
                           u.username,
                           m.sender_name,
                           'Система'
                       ) as manager_name
                FROM avito_messages m
                LEFT JOIN users u ON m.manager_id = u.id
                WHERE m.chat_id = ?
                ORDER BY m.timestamp ASC
                LIMIT ? OFFSET ?
            """,
                (chat_id, safe_limit, safe_offset),
            ).fetchall()
        else:
            messages = self.conn.execute(
                """
                SELECT m.*, 
                       COALESCE(u.username, m.sender_name, 'Система') as manager_name
                FROM avito_messages m
                LEFT JOIN users u ON m.manager_id = u.id
                WHERE m.chat_id = ?
                ORDER BY m.timestamp ASC
                LIMIT ? OFFSET ?
            """,
                (chat_id, safe_limit, safe_offset),
            ).fetchall()

        logger.info(f"[GET MESSAGES] Найдено сообщений в БД: {len(messages)}")

        total = self.conn.execute(
            "SELECT COUNT(*) as count FROM avito_messages WHERE chat_id = ?", (chat_id,)
        ).fetchone()["count"]

        logger.info(f"[GET MESSAGES] Всего сообщений в БД для чата {chat_id}: {total}")

        messages_list = [dict(msg) for msg in messages]

        if len(messages_list) > 0:
            logger.info(
                f"[GET MESSAGES] Первое сообщение: id={messages_list[0].get('id')}, text={messages_list[0].get('message_text', '')[:50]}..."
            )
        else:
            logger.warning(f"[GET MESSAGES] ⚠️ Сообщений нет в БД для чата {chat_id}!")
            # Проверяем, есть ли last_message в таблице чатов (для диагностики)
            chat_info = self.conn.execute(
                "SELECT last_message, client_name, chat_id FROM avito_chats WHERE id = ?",
                (chat_id,),
            ).fetchone()
            if chat_info and chat_info.get("last_message"):
                last_msg_text = self.clean_json_message(chat_info["last_message"])
                logger.warning("[GET MESSAGES] ⚠️ В avito_chats.last_message есть данные, но в avito_messages нет!")
                logger.warning(
                    "[GET MESSAGES] Это означает, что синхронизация сообщений не работает или сообщения не сохраняются в БД."
                )
                logger.warning(
                    f"[GET MESSAGES] chat_id в БД: {chat_info.get('chat_id')}, last_message: {last_msg_text[:100]}"
                )

        return messages_list, total

    def sync_chat_messages(self, chat_id: int, user_id: str, avito_chat_id: str) -> int:
        """
        Синхронизировать сообщения чата с Avito API

        Args:
            chat_id: ID чата в БД
            user_id: user_id Avito
            avito_chat_id: chat_id в Avito

        Returns:
            int: Количество загруженных новых сообщений
        """
        if not self.api:
            logger.warning("[SYNC MESSAGES] Синхронизация сообщений пропущена: API клиент не инициализирован")
            return 0
        try:
            logger.info(
                f"[SYNC MESSAGES] Загружаем сообщения из Avito API для чата {chat_id}, user_id={user_id}, avito_chat_id={avito_chat_id}"
            )
            # Получаем сообщения из API
            messages_data = self.api.get_chat_messages(user_id=user_id, chat_id=avito_chat_id, limit=100, offset=0)

            logger.info(f"[SYNC MESSAGES] Получен ответ от Avito API, тип: {type(messages_data)}")
            logger.info(f"[SYNC MESSAGES] Полный ответ (первые 500 символов): {str(messages_data)[:500]}")

            # Извлекаем список
            if isinstance(messages_data, list):
                messages_list = messages_data
                logger.info(f"[SYNC MESSAGES] Ответ - массив, количество сообщений: {len(messages_list)}")
                if len(messages_list) > 0:
                    logger.info(f"[SYNC MESSAGES] Первое сообщение из массива: {messages_list[0]}")
                    logger.info(f"[SYNC MESSAGES] Последнее сообщение из массива: {messages_list[-1]}")
            elif isinstance(messages_data, dict):
                # Пробуем разные ключи для извлечения сообщений
                logger.info(f"[SYNC MESSAGES] Ответ - объект, все ключи: {list(messages_data.keys())}")
                messages_list = messages_data.get(
                    "messages",
                    messages_data.get("items", messages_data.get("data", [])),
                )
                logger.info(f"[SYNC MESSAGES] Извлечено сообщений: {len(messages_list)}")
                if len(messages_list) > 0:
                    logger.info(f"[SYNC MESSAGES] Первое сообщение из объекта: {messages_list[0]}")
                    logger.info(f"[SYNC MESSAGES] Последнее сообщение из объекта: {messages_list[-1]}")
                else:
                    # Логируем структуру ответа, если сообщений нет
                    logger.warning(
                        f"[SYNC MESSAGES] ⚠️ Сообщений нет в ответе! Структура ответа: {list(messages_data.keys())}"
                    )
                    for key in messages_data.keys():
                        value = messages_data[key]
                        if isinstance(value, (list, dict)):
                            logger.warning(
                                f"[SYNC MESSAGES] Ключ '{key}': тип={type(value)}, длина/размер={len(value) if hasattr(value, '__len__') else 'N/A'}"
                            )
                        else:
                            logger.warning(
                                f"[SYNC MESSAGES] Ключ '{key}': тип={type(value)}, значение={str(value)[:100]}"
                            )
            else:
                messages_list = []
                logger.warning(
                    f"[SYNC MESSAGES] Неожиданный тип ответа: {type(messages_data)}, значение: {str(messages_data)[:500]}"
                )

            new_count = 0
            skipped_count = 0
            error_count = 0

            logger.info(f"[SYNC MESSAGES] Обрабатываем {len(messages_list)} сообщений из Avito API")

            for idx, msg_data in enumerate(messages_list):
                if not isinstance(msg_data, dict):
                    logger.warning(f"[SYNC MESSAGES] Сообщение {idx} не является словарем: {type(msg_data)}")
                    skipped_count += 1
                    continue

                msg_text = self.extract_text_from_message(msg_data)
                if not msg_text or not msg_text.strip():
                    if idx < 5:  # Логируем первые 5 пустых сообщений для диагностики
                        logger.warning(
                            f"[SYNC MESSAGES] Сообщение {idx} пустое или не содержит текста. msg_data keys: {list(msg_data.keys())}"
                        )
                        logger.warning(f"[SYNC MESSAGES] Полный msg_data для сообщения {idx}: {msg_data}")
                    skipped_count += 1
                    continue

                if idx < 3:  # Логируем первые 3 успешно извлеченных сообщения
                    raw_timestamp = msg_data.get("created", msg_data.get("created_at", msg_data.get("timestamp")))
                    logger.info(
                        f"[SYNC MESSAGES] Сообщение {idx}: text={msg_text[:50]}..., keys={list(msg_data.keys())}, raw_timestamp={raw_timestamp}, type={type(raw_timestamp)}"
                    )

                # Определяем тип сообщения
                # Avito API может использовать разные структуры:
                # 1. direction ('in'/'out') - приоритетный способ (новый формат)
                # 2. author_id (число) - сравниваем с user_id
                # 3. author.id или from.id - старый формат
                msg_author_id = None
                msg_type = None

                # Приоритет 1: используем direction, если есть
                if "direction" in msg_data:
                    direction = msg_data.get("direction", "").lower()
                    msg_type = "outgoing" if direction == "out" else "incoming"
                # Приоритет 2: используем author_id
                elif "author_id" in msg_data:
                    msg_author_id = str(msg_data["author_id"])
                    is_from_shop = msg_author_id == str(user_id)
                    msg_type = "outgoing" if is_from_shop else "incoming"
                # Приоритет 3: старый формат с author/from
                else:
                    author_data = msg_data.get("author", msg_data.get("from", {}))
                    if isinstance(author_data, dict):
                        msg_author_id = str(author_data.get("id", ""))
                        is_from_shop = msg_author_id == str(user_id) if msg_author_id else False
                        msg_type = "outgoing" if is_from_shop else "incoming"
                    else:
                        msg_type = "incoming"  # По умолчанию входящее

                # Получаем timestamp из API - это время, когда сообщение было отправлено клиентом
                timestamp = msg_data.get("created", msg_data.get("created_at", msg_data.get("timestamp")))
                if not timestamp:
                    # Если timestamp нет, используем текущее время (но это нежелательно)
                    timestamp = datetime.now(timezone.utc).isoformat()
                    logger.warning(
                        f"[SYNC MESSAGES] Сообщение без timestamp, используется текущее время: {msg_text[:50]}"
                    )
                else:
                    # Преобразуем timestamp в ISO формат с UTC
                    try:
                        if isinstance(timestamp, (int, float)):
                            # Unix timestamp (секунды) - преобразуем из UTC
                            # Avito API возвращает timestamp в UTC
                            timestamp_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            timestamp = timestamp_dt.isoformat()
                        elif isinstance(timestamp, str):
                            # Если это строка, проверяем формат
                            if "T" in timestamp:
                                # ISO формат - парсим с учетом часового пояса
                                try:
                                    timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                    if timestamp_dt.tzinfo is None:
                                        # Если нет часового пояса, считаем UTC
                                        timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                                    timestamp = timestamp_dt.isoformat()
                                except ValueError:
                                    # Если не удалось распарсить, используем текущее время
                                    timestamp = datetime.now(timezone.utc).isoformat()
                                    logger.warning(
                                        f"[SYNC MESSAGES] Не удалось распарсить timestamp '{timestamp}', используется текущее время"
                                    )
                            else:
                                # Другой формат строки - пробуем распарсить
                                try:
                                    # Пробуем как число в строке
                                    timestamp_num = float(timestamp)
                                    timestamp_dt = datetime.fromtimestamp(timestamp_num, tz=timezone.utc)
                                    timestamp = timestamp_dt.isoformat()
                                except (ValueError, OSError):
                                    timestamp = datetime.now(timezone.utc).isoformat()
                                    logger.warning(
                                        f"[SYNC MESSAGES] Не удалось распарсить timestamp '{timestamp}', используется текущее время"
                                    )
                        else:
                            # Неизвестный тип - используем текущее время
                            timestamp = datetime.now(timezone.utc).isoformat()
                            logger.warning(
                                f"[SYNC MESSAGES] Неизвестный тип timestamp: {type(timestamp)}, используется текущее время"
                            )
                    except (ValueError, OSError) as e:
                        timestamp = datetime.now(timezone.utc).isoformat()
                        logger.warning(f"[SYNC MESSAGES] Ошибка обработки timestamp: {e}, используется текущее время")

                # Имя отправителя
                chat_info = self.conn.execute("SELECT client_name FROM avito_chats WHERE id = ?", (chat_id,)).fetchone()

                # Определяем is_from_shop для имени отправителя
                is_from_shop = msg_type == "outgoing"
                sender_name = "Магазин" if is_from_shop else (chat_info["client_name"] if chat_info else "Клиент")

                # Проверяем дубликаты
                existing = self.conn.execute(
                    """
                    SELECT id FROM avito_messages
                    WHERE chat_id = ? AND message_text = ? AND message_type = ? AND timestamp = ?
                    LIMIT 1
            """,
                    (chat_id, msg_text, msg_type, timestamp),
                ).fetchone()

                if not existing:
                    self.conn.execute(
                        """
                        INSERT INTO avito_messages (chat_id, message_text, message_type, sender_name, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (chat_id, msg_text, msg_type, sender_name, timestamp),
                    )
                    new_count += 1
                    # Логируем сохранение timestamp для первых 3 сообщений
                    if idx < 3:
                        logger.info(
                            f"[SYNC MESSAGES] Сохранено сообщение: chat_id={chat_id}, type={msg_type}, timestamp={timestamp}"
                        )

            self.conn.commit()
            logger.info(
                f"[SYNC MESSAGES] Итоги синхронизации для чата {chat_id}: получено={len(messages_list)}, сохранено={new_count}, пропущено={skipped_count}, ошибок={error_count}"
            )

            # Обновляем response_timer на основе последнего неотвеченного входящего сообщения
            # Вычисляем время в Python для корректной обработки ISO формата
            try:
                # Получаем все сообщения чата для правильного сравнения timestamp
                all_messages = self.conn.execute(
                    """
                    SELECT message_type, timestamp
                    FROM avito_messages
                    WHERE chat_id = ?
                    ORDER BY timestamp DESC
                """,
                    (chat_id,),
                ).fetchall()

                # Находим последнее неотвеченное входящее сообщение
                last_outgoing_time = None
                last_unanswered_time = None

                # Логируем первые 3 сообщения для отладки
                debug_count = 0

                # Сравниваем timestamp как строки ISO (они сравниваются лексикографически правильно)
                # ISO формат: YYYY-MM-DDTHH:MM:SS, поэтому строковое сравнение работает корректно
                for msg in all_messages:
                    msg_dict = dict(msg) if not isinstance(msg, dict) else msg
                    msg_type = msg_dict.get("message_type")
                    msg_timestamp = msg_dict.get("timestamp")

                    if not msg_timestamp:
                        continue

                    # Логируем первые 3 сообщения для отладки
                    if debug_count < 3:
                        logger.info(
                            f"[SYNC MESSAGES] 🔍 Сообщение для таймера: chat_id={chat_id}, type={msg_type}, timestamp={msg_timestamp}"
                        )
                        debug_count += 1

                    if msg_type == "outgoing":
                        if last_outgoing_time is None or str(msg_timestamp) > str(last_outgoing_time):
                            last_outgoing_time = msg_timestamp
                            if debug_count <= 3:
                                logger.info(f"[SYNC MESSAGES] 📤 Обновлен last_outgoing_time: {last_outgoing_time}")
                    elif msg_type == "incoming":
                        # Проверяем, что это сообщение после последнего исходящего
                        if last_outgoing_time is None or str(msg_timestamp) > str(last_outgoing_time):
                            if last_unanswered_time is None or str(msg_timestamp) > str(last_unanswered_time):
                                last_unanswered_time = msg_timestamp
                                if debug_count <= 3:
                                    logger.info(
                                        f"[SYNC MESSAGES] 📥 Обновлен last_unanswered_time: {last_unanswered_time}"
                                    )

                timer_result = {"last_unanswered_time": last_unanswered_time} if last_unanswered_time else None

                if timer_result and timer_result.get("last_unanswered_time"):
                    last_unanswered_time_str = timer_result["last_unanswered_time"]
                    now = datetime.now(timezone.utc)

                    try:
                        # Парсим timestamp из ISO формата
                        if "T" in str(last_unanswered_time_str):
                            # ISO формат с T
                            if "+" in str(last_unanswered_time_str) or str(last_unanswered_time_str).endswith("Z"):
                                # С часовым поясом
                                last_time = datetime.fromisoformat(str(last_unanswered_time_str).replace("Z", "+00:00"))
                            else:
                                # Без часового пояса - считаем UTC
                                last_time = datetime.fromisoformat(str(last_unanswered_time_str))
                                if last_time.tzinfo is None:
                                    last_time = last_time.replace(tzinfo=timezone.utc)
                        else:
                            # Пробуем другие форматы
                            try:
                                last_time = datetime.fromisoformat(str(last_unanswered_time_str))
                                if last_time.tzinfo is None:
                                    last_time = last_time.replace(tzinfo=timezone.utc)
                            except:
                                # Если не получается, используем текущее время
                                last_time = now

                        # Вычисляем разницу в минутах
                        time_diff = now - last_time
                        timer_minutes = max(0, int(time_diff.total_seconds() / 60))

                        # Обновляем response_timer
                        self.conn.execute(
                            """
                            UPDATE avito_chats
                            SET response_timer = ?
                            WHERE id = ?
                        """,
                            (timer_minutes, chat_id),
                        )
                        self.conn.commit()
                        logger.info(
                            f"[SYNC MESSAGES] ⏱️ Обновлен response_timer для чата {chat_id}: {timer_minutes} минут (last_unanswered_time={last_unanswered_time_str}, parsed={last_time.isoformat()}, now={now.isoformat()}, diff={time_diff.total_seconds()/60:.2f} мин)"
                        )
                    except Exception as parse_error:
                        logger.warning(
                            f"[SYNC MESSAGES] Ошибка парсинга timestamp для чата {chat_id}: {parse_error}, timestamp: {last_unanswered_time_str}"
                        )
                        # Устанавливаем 0 при ошибке
                        self.conn.execute(
                            "UPDATE avito_chats SET response_timer = 0 WHERE id = ?",
                            (chat_id,),
                        )
                        self.conn.commit()
                else:
                    # Нет неотвеченных сообщений
                    self.conn.execute(
                        "UPDATE avito_chats SET response_timer = 0 WHERE id = ?",
                        (chat_id,),
                    )
                    self.conn.commit()
            except Exception as timer_error:
                logger.warning(f"[SYNC MESSAGES] Ошибка обновления response_timer для чата {chat_id}: {timer_error}")

            # Автоматически возвращаем чат из завершенных, если клиент написал новое сообщение
            try:
                # Проверяем, есть ли новые входящие сообщения после последнего исходящего
                if last_unanswered_time:
                    # Если есть неотвеченное сообщение, возвращаем чат из завершенных
                    result = self.conn.execute(
                        """
                        UPDATE avito_chats
                        SET status = 'active', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND status = 'completed'
                    """,
                        (chat_id,),
                    )
                    self.conn.commit()
                    if result.rowcount > 0:
                        logger.info(
                            f"[SYNC MESSAGES] ✅ Чат {chat_id} возвращен из завершенных (клиент написал новое сообщение)"
                        )
            except Exception as status_error:
                logger.warning(f"[SYNC MESSAGES] Ошибка возврата чата из завершенных: {status_error}")

            # Проверяем, сколько всего сообщений в БД после синхронизации
            total_in_db = self.conn.execute(
                "SELECT COUNT(*) as count FROM avito_messages WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()["count"]
            logger.info(f"[SYNC MESSAGES] Всего сообщений в БД для чата {chat_id}: {total_in_db}")

            return new_count

        except Exception as e:
            logger.error(
                f"[SYNC MESSAGES] Ошибка синхронизации сообщений чата {chat_id}: {e}",
                exc_info=True,
            )
            import traceback

            logger.error(f"[SYNC MESSAGES] Traceback: {traceback.format_exc()}")
            return 0

    def send_message(
        self, chat_id: int, message_text: str, manager_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Отправить сообщение в чат

        Args:
            chat_id: ID чата в БД
            message_text: Текст сообщения
            manager_id: ID менеджера (опционально)

        Returns:
            bool: True если успешно
        """
        if not message_text or len(message_text.strip()) == 0:
            return False, "Empty message"
        if len(message_text) > 5000:
            return False, "Message too long"
        # Получаем данные чата
        chat = self.conn.execute(
            """
            SELECT ac.*, s.client_id, s.client_secret, s.user_id
            FROM avito_chats ac
            JOIN avito_shops s ON ac.shop_id = s.id
            WHERE ac.id = ?
        """,
            (chat_id,),
        ).fetchone()

        if not chat:
            return False, "Chat not found"

        # Преобразуем sqlite3.Row в словарь для безопасного доступа
        chat = dict(chat) if not isinstance(chat, dict) else chat

        if not self.api or not chat.get("client_id") or not chat.get("client_secret") or not chat.get("user_id"):
            logger.error("Невозможно отправить сообщение: отсутствуют учетные данные Авито или API клиент")
            return False, "Avito credentials missing"

        try:
            logger.info(
                f"[SEND MESSAGE] MessengerService.send_message: chat_id={chat_id}, avito_chat_id={chat.get('chat_id')}, user_id={chat.get('user_id')}"
            )
            # Отправляем через API
            self.api.send_message(
                user_id=str(chat.get("user_id")),
                chat_id=str(chat.get("chat_id")),
                message=message_text,
            )

            # Сохраняем в БД с правильным sender_name
            # Получаем username отправителя для подписи (видна только в интерфейсе, не отправляется клиенту)
            sender_name = "Магазин"  # Значение по умолчанию
            if manager_id:
                user_row = self.conn.execute(
                    """
                    SELECT username FROM users WHERE id = ?
                """,
                    (manager_id,),
                ).fetchone()
                if user_row:
                    sender_name = (
                        dict(user_row).get("username", "Магазин")
                        if not isinstance(user_row, dict)
                        else user_row.get("username", "Магазин")
                    )

            self.conn.execute(
                """
                INSERT INTO avito_messages (chat_id, message_text, message_type, sender_name, manager_id)
                VALUES (?, ?, 'outgoing', ?, ?)
            """,
                (chat_id, message_text, sender_name, manager_id),
            )

            # Обновляем чат
            self.conn.execute(
                """
                UPDATE avito_chats
                SET last_message = ?, updated_at = CURRENT_TIMESTAMP, unread_count = 0
                WHERE id = ?
            """,
                (message_text, chat_id),
            )

            self.conn.commit()

            logger.info(f"Сообщение отправлено в чат {chat_id}")
            return True, None

        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}")
            return False, str(e)

    def take_from_pool(self, chat_id: int, manager_id: int) -> bool:
        """Взять чат из пула"""
        try:
            self.conn.execute(
                """
                UPDATE avito_chats
                SET assigned_manager_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND assigned_manager_id IS NULL
            """,
                (manager_id, chat_id),
            )
            self.conn.commit()
            return True
        except:
            return False

    def return_to_pool(self, chat_id: int) -> bool:
        """Вернуть чат в пул"""
        try:
            self.conn.execute(
                """
                UPDATE avito_chats
                SET assigned_manager_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (chat_id,),
            )
            self.conn.commit()
            return True
        except:
            return False

    def update_all_response_timers(self) -> Dict[str, int]:
        """
        Обновить response_timer для всех чатов

        Returns:
            Dict с результатами: {'updated': количество обновленных, 'errors': количество ошибок}
        """
        logger.info("[UPDATE TIMERS] Начало обновления таймеров для всех чатов")
        updated_count = 0
        error_count = 0

        try:
            # Получаем все активные чаты
            all_chats = self.conn.execute(
                """
                SELECT id FROM avito_chats
                WHERE status != 'completed' AND status != 'blocked'
            """
            ).fetchall()

            total_chats = len(all_chats)
            logger.info(f"[UPDATE TIMERS] Найдено {total_chats} чатов для обновления")

            now = datetime.now(timezone.utc)

            # Обрабатываем чаты батчами по 100
            batch_size = 100
            for i in range(0, total_chats, batch_size):
                batch = all_chats[i : i + batch_size]
                chat_ids = [chat["id"] if isinstance(chat, dict) else chat[0] for chat in batch]

                # Получаем все сообщения для этого батча
                all_messages = self.conn.execute(
                    """
                    SELECT chat_id, message_type, timestamp
                    FROM avito_messages
                    WHERE chat_id IN ({})
                    ORDER BY chat_id, timestamp DESC
                """.format(
                        ",".join("?" * len(chat_ids))
                    ),
                    chat_ids,
                ).fetchall()

                # Группируем по чатам

                chat_last_outgoing = {}
                chat_last_unanswered = {}

                for msg in all_messages:
                    msg_dict = dict(msg) if not isinstance(msg, dict) else msg
                    chat_id = msg_dict.get("chat_id")
                    msg_type = msg_dict.get("message_type")
                    msg_timestamp = msg_dict.get("timestamp")

                    if not chat_id or not msg_timestamp:
                        continue

                    if msg_type == "outgoing":
                        if chat_id not in chat_last_outgoing or str(msg_timestamp) > str(chat_last_outgoing[chat_id]):
                            chat_last_outgoing[chat_id] = msg_timestamp
                    elif msg_type == "incoming":
                        last_outgoing = chat_last_outgoing.get(chat_id)
                        if last_outgoing is None or str(msg_timestamp) > str(last_outgoing):
                            if chat_id not in chat_last_unanswered or str(msg_timestamp) > str(
                                chat_last_unanswered[chat_id]
                            ):
                                chat_last_unanswered[chat_id] = msg_timestamp

                # Обновляем таймеры для этого батча
                for chat_id in chat_ids:
                    try:
                        last_unanswered_time_str = chat_last_unanswered.get(chat_id)

                        if last_unanswered_time_str:
                            # Парсим timestamp
                            try:
                                if "T" in str(last_unanswered_time_str):
                                    if "+" in str(last_unanswered_time_str) or str(last_unanswered_time_str).endswith(
                                        "Z"
                                    ):
                                        last_time = datetime.fromisoformat(
                                            str(last_unanswered_time_str).replace("Z", "+00:00")
                                        )
                                    else:
                                        last_time = datetime.fromisoformat(str(last_unanswered_time_str))
                                        if last_time.tzinfo is None:
                                            last_time = last_time.replace(tzinfo=timezone.utc)
                                else:
                                    try:
                                        last_time = datetime.fromisoformat(str(last_unanswered_time_str))
                                        if last_time.tzinfo is None:
                                            last_time = last_time.replace(tzinfo=timezone.utc)
                                    except:
                                        last_time = now

                                time_diff = now - last_time
                                timer_minutes = max(0, int(time_diff.total_seconds() / 60))

                                self.conn.execute(
                                    """
                                    UPDATE avito_chats
                                    SET response_timer = ?
                                    WHERE id = ?
                                """,
                                    (timer_minutes, chat_id),
                                )
                                updated_count += 1
                            except Exception as parse_error:
                                logger.warning(
                                    f"[UPDATE TIMERS] Ошибка парсинга timestamp для чата {chat_id}: {parse_error}"
                                )
                                self.conn.execute(
                                    "UPDATE avito_chats SET response_timer = 0 WHERE id = ?",
                                    (chat_id,),
                                )
                                error_count += 1
                        else:
                            # Нет неотвеченных сообщений
                            self.conn.execute(
                                "UPDATE avito_chats SET response_timer = 0 WHERE id = ?",
                                (chat_id,),
                            )
                            updated_count += 1
                    except Exception as chat_error:
                        logger.warning(f"[UPDATE TIMERS] Ошибка обновления таймера для чата {chat_id}: {chat_error}")
                        error_count += 1

                # Коммитим батч
                self.conn.commit()

                if (i + batch_size) % 500 == 0:
                    logger.info(f"[UPDATE TIMERS] Обработано {min(i + batch_size, total_chats)}/{total_chats} чатов")

            logger.info(f"[UPDATE TIMERS] ✅ Обновление завершено: обновлено={updated_count}, ошибок={error_count}")
            return {"updated": updated_count, "errors": error_count}

        except Exception as e:
            logger.error(
                f"[UPDATE TIMERS] Критическая ошибка при обновлении таймеров: {e}",
                exc_info=True,
            )
            return {"updated": updated_count, "errors": error_count + 1}

    def auto_complete_old_chats(self, days: int = 1) -> Dict[str, int]:
        """
        Автоматически завершить чаты, где последнее сообщение от менеджера было больше N дней назад

        Args:
            days: Количество дней (по умолчанию 1)

        Returns:
            Dict с результатами: {'completed': количество завершенных, 'errors': количество ошибок}
        """
        logger.info(f"[AUTO COMPLETE] Начало автозавершения чатов старше {days} дней")
        completed_count = 0
        error_count = 0

        try:
            from datetime import timedelta

            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_time.isoformat()

            # Находим чаты, где последнее сообщение от менеджера было больше N дней назад
            # И чат не завершен и не заблокирован
            # Используем Python для правильного сравнения timestamp
            # НЕ проверяем назначение менеджера - завершаем все чаты независимо от назначения
            all_chats = self.conn.execute(
                """
                SELECT DISTINCT c.id, c.status
                FROM avito_chats c
                WHERE c.status != 'completed' 
                    AND c.status != 'blocked'
            """
            ).fetchall()

            old_chats = []
            for chat in all_chats:
                chat_id = chat["id"] if isinstance(chat, dict) else chat[0]

                # Получаем все сообщения чата
                messages = self.conn.execute(
                    """
                    SELECT message_type, timestamp
                    FROM avito_messages
                    WHERE chat_id = ?
                    ORDER BY timestamp DESC
                """,
                    (chat_id,),
                ).fetchall()

                if not messages:
                    continue

                # Находим последнее исходящее и последнее входящее сообщение
                last_outgoing_time = None
                last_incoming_time = None

                for msg in messages:
                    msg_dict = dict(msg) if not isinstance(msg, dict) else msg
                    msg_type = msg_dict.get("message_type")
                    msg_timestamp = msg_dict.get("timestamp")

                    if not msg_timestamp:
                        continue

                    if msg_type == "outgoing":
                        if last_outgoing_time is None or str(msg_timestamp) > str(last_outgoing_time):
                            last_outgoing_time = msg_timestamp
                    elif msg_type == "incoming":
                        if last_incoming_time is None or str(msg_timestamp) > str(last_incoming_time):
                            last_incoming_time = msg_timestamp

                # Проверяем условия:
                # 1. Есть исходящие сообщения
                # 2. Нет входящих сообщений после последнего исходящего (или входящие старше исходящего)
                # 3. Последнее исходящее сообщение старше N дней
                if last_outgoing_time:
                    # Проверяем, что нет входящих после последнего исходящего
                    has_unanswered = False
                    if last_incoming_time and str(last_incoming_time) > str(last_outgoing_time):
                        has_unanswered = True

                    if not has_unanswered:
                        # Парсим timestamp последнего исходящего сообщения
                        try:
                            if "T" in str(last_outgoing_time):
                                last_outgoing_dt = datetime.fromisoformat(
                                    str(last_outgoing_time).replace("Z", "+00:00")
                                )
                                if last_outgoing_dt.tzinfo is None:
                                    last_outgoing_dt = last_outgoing_dt.replace(tzinfo=timezone.utc)
                            else:
                                try:
                                    last_outgoing_dt = datetime.fromisoformat(str(last_outgoing_time))
                                    if last_outgoing_dt.tzinfo is None:
                                        last_outgoing_dt = last_outgoing_dt.replace(tzinfo=timezone.utc)
                                except:
                                    continue

                            # Проверяем, что последнее исходящее сообщение старше N дней
                            if last_outgoing_dt < cutoff_time:
                                old_chats.append(chat)
                        except Exception as parse_err:
                            logger.warning(f"[AUTO COMPLETE] Ошибка парсинга timestamp для чата {chat_id}: {parse_err}")
                            continue

            logger.info(f"[AUTO COMPLETE] Найдено {len(old_chats)} чатов для завершения")

            for chat in old_chats:
                try:
                    chat_id = chat["id"] if isinstance(chat, dict) else chat[0]
                    (
                        chat.get("status") if isinstance(chat, dict) else (chat[1] if len(chat) > 1 else None)
                    )

                    # Завершаем чат
                    self.conn.execute(
                        """
                        UPDATE avito_chats
                        SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (chat_id,),
                    )
                    completed_count += 1

                    if completed_count % 100 == 0:
                        logger.info(f"[AUTO COMPLETE] Завершено {completed_count} чатов...")

                except Exception as chat_error:
                    logger.warning(f"[AUTO COMPLETE] Ошибка завершения чата {chat_id}: {chat_error}")
                    error_count += 1

            self.conn.commit()
            logger.info(
                f"[AUTO COMPLETE] ✅ Автозавершение завершено: завершено={completed_count}, ошибок={error_count}"
            )
            return {"completed": completed_count, "errors": error_count}

        except Exception as e:
            logger.error(
                f"[AUTO COMPLETE] Критическая ошибка при автозавершении чатов: {e}",
                exc_info=True,
            )
            return {"completed": completed_count, "errors": error_count + 1}

    def block_user(self, chat_id: int, user_id: str, avito_chat_id: str, block: bool = True) -> bool:
        """Заблокировать/разблокировать пользователя"""
        try:
            self.api.block_user(user_id=user_id, chat_id=avito_chat_id, block=block)

            new_status = "blocked" if block else "active"
            self.conn.execute(
                """
                UPDATE avito_chats SET status = ? WHERE id = ?
            """,
                (new_status, chat_id),
            )
            self.conn.commit()

            return True
        except:
            return False
