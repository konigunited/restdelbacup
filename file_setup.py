import os

# Создание всех директорий
os.makedirs('src/bot', exist_ok=True)
os.makedirs('src/claude', exist_ok=True)
os.makedirs('src/sheets', exist_ok=True)

# __init__.py файлы
init_files = [
    'src/__init__.py',
    'src/bot/__init__.py', 
    'src/claude/__init__.py',
    'src/sheets/__init__.py'
]


for file in init_files:
    with open(file, 'w') as f:
        f.write('# Package initialization\n')

print("✅ Структура создана! Теперь заполни основные файлы.")py