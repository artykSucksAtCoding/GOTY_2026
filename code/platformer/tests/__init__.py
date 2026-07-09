"""Пакет с юнит-тестами игры.

Запуск всех тестов из корня репозитория:
    python -m unittest discover -s code/platformer/tests -t code/platformer -v

(параметр -t code/platformer нужен, чтобы модули игры импортировались как
`import settings`, `import leaderboard` и т.п. — так же, как это делает сама
игра, а не как `code.platformer.settings`).
"""
