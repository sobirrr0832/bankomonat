FROM python:3.9-slim

# Ishchi direktoriyani o'rnatish
WORKDIR /app

# Kerakli Python paketlarini o'rnatish uchun requirements.txt ni ko'chirish
COPY requirements.txt .

# Paketlarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Dastur fayllarini ko'chirish
COPY . .

# Portni ochish
EXPOSE $PORT

# Applicationni ishga tushirish
CMD gunicorn --bind 0.0.0.0:$PORT main:app
