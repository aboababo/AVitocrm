#!/usr/bin/env python3
"""
Утилита для инициализации базы данных OSAGAMING CRM
Автоматически создает базу данных и таблицы если они не существуют
"""

import sys
import os
import logging

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция инициализации базы данных"""
    print("=" * 60)
    print("🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ OSAGAMING CRM")
    print("=" * 60)
    
    try:
        # Импортируем модули
        print("📦 Импортирование модулей...")
        from app.core.database import initialize_database, get_database_status
        from app.core.config_simple import settings
        print("✅ Модули успешно импортированы")
        
        # Проверяем текущий статус БД
        print("\n📊 Проверка текущего состояния базы данных...")
        db_status = get_database_status()
        
        print(f"   📁 Файл БД существует: {'✅' if db_status['file_exists'] else '❌'}")
        print(f"   🔗 Подключение: {'✅' if db_status['connected'] else '❌'}")
        print(f"   📋 Таблицы созданы: {'✅' if db_status['tables_exist'] else '❌'}")
        print(f"   📊 Есть данные: {'✅' if db_status['has_data'] else '❌'}")
        
        if db_status['path']:
            print(f"   📍 Путь к БД: {db_status['path']}")
        
        # Инициализируем БД если необходимо
        if not db_status['connected'] or not db_status['tables_exist']:
            print("\n🚀 Инициализация базы данных...")
            
            if initialize_database():
                print("✅ База данных успешно инициализирована!")
                
                # Проверяем результат
                new_status = get_database_status()
                print("\n📊 Новое состояние базы данных:")
                print(f"   📁 Файл БД существует: {'✅' if new_status['file_exists'] else '❌'}")
                print(f"   🔗 Подключение: {'✅' if new_status['connected'] else '❌'}")
                print(f"   📋 Таблицы созданы: {'✅' if new_status['tables_exist'] else '❌'}")
                print(f"   📊 Есть данные: {'✅' if new_status['has_data'] else '❌'}")
                
                if new_status['connected'] and new_status['tables_exist']:
                    print("\n🎉 База данных готова к использованию!")
                    return True
                else:
                    print("\n❌ Инициализация завершена с ошибками")
                    return False
            else:
                print("\n❌ Ошибка инициализации базы данных")
                return False
        else:
            print("\n✅ База данных уже инициализирована")
            return True
            
    except ImportError as e:
        print(f"\n❌ Ошибка импорта модулей: {e}")
        print("💡 Убедитесь, что вы находитесь в директории backend/")
        return False
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return False

def check_requirements():
    """Проверка требований для запуска"""
    print("🔍 Проверка требований...")
    
    # Проверяем Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print(f"❌ Требуется Python 3.8+, найден: {python_version.major}.{python_version.minor}")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}")
    
    # Проверяем наличие файлов
    required_files = [
        'app/__init__.py',
        'app/core/config_simple.py',
        'app/core/database.py',
        'app/models/__init__.py',
        'requirements.txt'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"\n❌ Отсутствуют файлы: {missing_files}")
        print("💡 Убедитесь, что вы находитесь в правильной директории")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Запуск утилиты инициализации базы данных...")
    
    # Проверяем требования
    if not check_requirements():
        print("\n❌ Требования не выполнены")
        sys.exit(1)
    
    # Запускаем инициализацию
    success = main()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print("\n📋 Следующие шаги:")
        print("   1. Запустите сервер: python -m uvicorn app.main:app --reload")
        print("   2. Откройте API документацию: http://localhost:8000/docs")
        print("   3. Проверьте health endpoint: http://localhost:8000/health")
        print("\n🔑 Тестовый пользователь:")
        print("   Email: admin@osagaming.com")
        print("   Password: password")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА С ОШИБКАМИ")
        print("=" * 60)
        print("\n🔧 Возможные решения:")
        print("   1. Проверьте права доступа к директории")
        print("   2. Убедитесь, что все зависимости установлены")
        print("   3. Проверьте логи для получения детальной информации")
        sys.exit(1)