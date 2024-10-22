# eoa_test

Это проект Django, который включает Gunicorn, Nginx и Docker для развёртывания веб-приложения.

## Требования

Перед тем, как начать, убедитесь, что у вас установлены следующие программы:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Установка и запуск

Следуйте этим инструкциям, чтобы запустить проект локально.

### Шаги для Windows

1. Клонируйте репозиторий:

   ```sh
   git clone https://github.com/Alan69/eoa_test.git
   cd eoa_test
   ```

2. Соберите и запустите контейнеры Docker:

```
docker-compose up --build
```

Шаги для Linux и MacOS
1. Клонируйте репозиторий:

```
git clone https://github.com/Alan69/eoa_test.git
cd eoa_test
```

2. Соберите и запустите контейнеры Docker:

```
sudo docker-compose up --build
```

Доступ к приложению
После успешного запуска контейнеров приложение будет доступно по адресу http://localhost.

Управление статическими файлами
Для сбора статических файлов используйте следующую команду:

```
sudo docker-compose exec app python manage.py collectstatic
```

Автор
Alan69