# DocuMind

DocuMind — REST API для загрузки текстовых документов и поиска по ним. Сервис принимает TXT-файлы, сохраняет документы и их фрагменты в SQLite, а на вопрос возвращает наиболее релевантный фрагмент вместе с именем исходного файла.

Поиск использует TF-IDF и cosine similarity. Найденный фрагмент возвращается как есть: проект не генерирует ответ с помощью LLM и не требует внешних API.

## Возможности

- Загрузка TXT с проверкой расширения, размера, UTF-8-кодировки и пустого содержимого.
- Проверка дубликатов по SHA-256.
- Разбиение документов на перекрывающиеся chunks и сохранение их в SQLite.
- Список загруженных документов.
- Поиск и ранжирование chunks по вопросу с минимальным порогом релевантности.
- Возврат текста найденного chunk, исходного имени файла и relevance score.

## Стек технологий

- Python 3.11+
- FastAPI и Uvicorn
- Pydantic 2 и pydantic-settings
- SQLAlchemy 2 и SQLite
- scikit-learn (`TfidfVectorizer`, cosine similarity)
- pytest и FastAPI TestClient

## Архитектура

Запросы проходят через API-роутеры. Схемы Pydantic проверяют запросы и формируют ответы. Сервис chunking делит текст на фрагменты, `DocumentRepository` сохраняет и читает документы с chunks, а `SearchService` выполняет поиск по сохранённым chunks. SQLAlchemy-модели описывают таблицы документов и фрагментов.

При старте приложения SQLAlchemy создаёт отсутствующие таблицы. Для новой установки миграции не требуются. `create_all()` не изменяет уже существующие таблицы при изменении модели.

## Структура проекта

```text
app/
├── api/v1/             # маршруты health, documents и questions
├── core/               # конфигурация приложения
├── db/                 # SQLAlchemy Base, engine и сессии
├── models/              # модели Document и Chunk
├── repositories/        # доступ к документам и chunks
├── schemas/             # Pydantic-схемы для Question API
└── services/            # chunking и TF-IDF-поиск
tests/                   # тесты API, chunking и поиска
requirements.txt         # runtime-зависимости
requirements-dev.txt     # runtime и зависимости тестирования
.env.example             # пример конфигурации
```

## Как работает поиск

### Chunking

По умолчанию текст делится на фрагменты до 1000 символов с overlap 200 символов. Следующий фрагмент начинается после предыдущего на `chunk_size - chunk_overlap` символов. Overlap сохраняет контекст на границах фрагментов. Разбиение символьное, а не по предложениям или словам.

### TF-IDF

При каждом поиске `TfidfVectorizer` строит словарь и рассчитывает важность слов по всем сохранённым chunks. Частые во всём корпусе слова получают меньший вес, а более характерные для отдельных фрагментов — больший. Вектор запроса преобразуется тем же словарём; слова, которых нет в корпусе, не участвуют в поиске.

### Cosine Similarity

Cosine similarity сравнивает вектор вопроса с векторами chunks и даёт score от 0 до 1. Чем выше score, тем ближе текст фрагмента к запросу по совпадающим словам. Результаты с нулевым score или ниже `MIN_RELEVANCE_THRESHOLD` не возвращаются. Это лексический поиск: он не понимает синонимы и смысловые перефразирования.

## Установка и запуск

Требуется Python 3.11 или новее. Команды ниже выполняются из корневой папки репозитория.

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Если команда `python3.11` в системе называется иначе, используйте путь к установленному Python 3.11+.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Конфигурация

Конфигурация необязательна: приложение использует значения по умолчанию. Чтобы настроить её через `.env`, скопируйте пример:

```bash
cp .env.example .env
```

В PowerShell:

```powershell
Copy-Item .env.example .env
```

Доступные переменные:

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `APP_NAME` | `RAG API` | Название приложения в FastAPI |
| `API_V1_PREFIX` | `/api/v1` | Префикс API версии 1 |
| `DATABASE_URL` | `sqlite:///./rag.db` | URL базы данных; SQLite-файл создаётся относительно текущей папки запуска |
| `DEBUG` | `false` | Режим отладки FastAPI |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Максимальный размер файла в байтах, по умолчанию 10 MiB |
| `CHUNK_SIZE` | `1000` | Размер chunk в символах |
| `CHUNK_OVERLAP` | `200` | Перекрытие chunks в символах; должно быть меньше `CHUNK_SIZE` |
| `MIN_RELEVANCE_THRESHOLD` | `0.1` | Минимальный score в диапазоне от 0 до 1 |

После изменения `.env` перезапустите приложение: настройки считываются при старте.

### Запуск сервера

```bash
python -m uvicorn app.main:app --reload
```

Сервер доступен по адресу `http://127.0.0.1:8000`. Интерактивная документация Swagger UI: `http://127.0.0.1:8000/docs`. OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`.

При запуске из корня проекта база по умолчанию хранится в `./rag.db`. Файл базы данных игнорируется Git.

## API

Все маршруты, кроме документации FastAPI, используют префикс `/api/v1`.

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Проверка доступности приложения |
| `POST` | `/api/v1/documents/upload` | Загрузка TXT как `multipart/form-data`, поле `file` |
| `GET` | `/api/v1/documents` | Список документов и сохранённых chunks |
| `POST` | `/api/v1/questions/ask` | Поиск наиболее релевантного chunk по вопросу |

### Проверка сервиса

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Ответ:

```json
{"status":"ok"}
```

### Загрузка документа

```bash
curl -X POST \
  -F "file=@./document.txt;type=text/plain" \
  http://127.0.0.1:8000/api/v1/documents/upload
```

Успешная загрузка возвращает `201 Created`. Пример ответа:

```json
{
  "id": 1,
  "filename": "document.txt",
  "content_type": "text/plain",
  "content_sha256": "71d94aa83a496ef9f42bf9983bd9d115063e2ee82354e1b087a816f7278829fd",
  "size_bytes": 17,
  "created_at": "2026-11-20T12:00:00",
  "chunks": [
    {
      "id": 1,
      "content": "Stars emit light.",
      "chunk_index": 0
    }
  ]
}
```

### Список документов

```bash
curl http://127.0.0.1:8000/api/v1/documents
```

Ответ — массив документов в том же формате, что и ответ загрузки. Если документов ещё нет, возвращается пустой массив `[]`.

### Вопрос по документам

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"question":"How do stars emit light?"}' \
  http://127.0.0.1:8000/api/v1/questions/ask
```

Тело запроса:

```json
{
  "question": "How do stars emit light?"
}
```

Успешный ответ (`200 OK`):

```json
{
  "answer": "Stars emit light.",
  "source_filename": "document.txt",
  "relevance_score": 1.0
}
```

`answer` — текст найденного фрагмента, а не сгенерированный ответ. `relevance_score` — cosine similarity для лучшего совпадения.

## Обработка ошибок

| Ситуация | HTTP-код | Пример ответа |
| --- | --- | --- |
| Вопрос пустой или содержит только пробелы | `422` | FastAPI validation error |
| Документов ещё нет | `404` | `{"detail":"No documents are available"}` |
| Нет совпадения выше порога | `404` | `{"detail":"No relevant document found"}` |
| Загружен файл не `.txt` | `415` | `{"detail":"Only TXT files are supported"}` |
| Файл пустой или состоит из пробелов | `400` | `{"detail":"File is empty"}` |
| Файл не декодируется как UTF-8 | `400` | `{"detail":"File must use UTF-8 encoding"}` |
| Размер больше лимита | `413` | `{"detail":"File exceeds the maximum allowed size"}` |
| Файл с таким SHA-256 уже загружен | `409` | `{"detail":"This document has already been uploaded"}` |

## Тесты

Установите runtime- и тестовые зависимости, активируйте виртуальное окружение и запустите pytest через тот же Python, которым установлены зависимости:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Тесты используют временные SQLite-базы и FastAPI TestClient; пользовательская база `rag.db` для тестирования не нужна.

## Ограничения и возможные улучшения

- Поддерживаются только TXT-файлы в UTF-8; PDF, DOCX, OCR и другие форматы не реализованы.
- Поиск основан на совпадении слов и не находит смысловые перефразирования или синонимы.
- TF-IDF пересчитывается по всем chunks при каждом вопросе; для больших корпусов можно кэшировать индекс или выбрать отдельное полнотекстовое хранилище.
- Chunks формируются по количеству символов, поэтому границы могут проходить внутри слова или предложения.
- SQLite и создание таблиц через `create_all()` рассчитаны на простой локальный запуск; для развёртывания и эволюции схемы можно добавить миграции.
- Сейчас нет аутентификации, пагинации списка документов, удаления документов и ограничений частоты запросов.
