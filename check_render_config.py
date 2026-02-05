#!/usr/bin/env python3
"""
Проверка конфигурации перед развертыванием на Render.com
"""
import os
import sys
from pathlib import Path

def check_file_exists(path: str, name: str) -> bool:
    if Path(path).exists():
        print(f"✓ {name} найден: {path}")
        return True
    print(f"✗ {name} НЕ найден: {path}")
    return False

def check_content(path: str, search_text: str, name: str) -> bool:
    if not Path(path).exists():
        return False
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        if search_text in content:
            print(f"✓ {name} содержит '{search_text}'")
            return True
    print(f"✗ {name} НЕ содержит '{search_text}'")
    return False

def main():
    print("\n" + "="*60)
    print("Проверка конфигурации для Render.com")
    print("="*60 + "\n")
    
    all_ok = True
    
    # Проверка основных файлов
    print("📦 Проверка основных файлов:")
    all_ok &= check_file_exists("render.yaml", "render.yaml")
    all_ok &= check_file_exists("requirements.txt", "requirements.txt")
    all_ok &= check_file_exists("backend/main.py", "backend/main.py")
    all_ok &= check_file_exists("frontend/package.json", "frontend/package.json")
    all_ok &= check_file_exists("DEPLOY_RENDER.md", "DEPLOY_RENDER.md")
    
    print("\n📝 Проверка конфигурации:")
    # Проверка render.yaml конфигурации
    all_ok &= check_content("render.yaml", "gaming-ai-backend", "render.yaml - backend service")
    all_ok &= check_content("render.yaml", "gaming-ai-frontend", "render.yaml - frontend service")
    all_ok &= check_content("render.yaml", "GROQ_API_KEY", "render.yaml - GROQ_API_KEY env var")
    all_ok &= check_content("render.yaml", "VITE_API_URL", "render.yaml - VITE_API_URL env var")
    
    # Проверка FastAPI конфигурации
    all_ok &= check_content("backend/main.py", "uvicorn", "backend - uvicorn импорт")
    all_ok &= check_content("backend/main.py", "CORSMiddleware", "backend - CORS конфигурация")
    all_ok &= check_content("backend/main.py", "host 0.0.0.0", "backend - правильное значение host")
    
    # Проверка frontend конфигурации
    all_ok &= check_content("frontend/src/App.tsx", "VITE_API_URL", "frontend - использование VITE_API_URL")
    all_ok &= check_content("frontend/vite.config.mts", "preview", "frontend - preview конфигурация")
    
    print("\n" + "="*60)
    if all_ok:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Проект готов к развертыванию")
        print("\nСледующие шаги:")
        print("1. Загрузите проект на GitHub")
        print("2. Перейдите на https://render.com")
        print("3. Создайте новый Blueprint из вашего репозитория")
        print("4. Добавьте переменную окружения GROQ_API_KEY")
        print("5. Нажмите 'Deploy'")
        print("\nПодробные инструкции в: DEPLOY_RENDER.md")
        sys.exit(0)
    else:
        print("❌ НАЙДЕНЫ ПРОБЛЕМЫ! Исправьте ошибки перед развертыванием")
        sys.exit(1)

if __name__ == "__main__":
    main()
