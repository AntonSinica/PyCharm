import mysql.connector  # Импортируем библиотеку для работы с MySQL

try:
    # Подключение к базе данных
    db = mysql.connector.connect(
        host="localhost",  # Адрес сервера базы данных
        user="root",  # Имя пользователя
        password="lthse2022-2",  # Пароль пользователя (замените на ваш пароль)
        database="task_manager"  # Имя базы данных
    )

    # Создание курсора для выполнения SQL-запросов
    cursor = db.cursor()

    # Выполнение тестового запроса для получения всех пользователей
    cursor.execute("SELECT * FROM users")

    # Вывод результатов запроса
    for row in cursor.fetchall():
        print(row)  # Выводим каждую строку из результата

    # Закрытие курсора и соединения
    cursor.close()
    db.close()

except mysql.connector.Error as err:
    # Обработка ошибок подключения
    print(f"Ошибка подключения к базе данных: {err}")