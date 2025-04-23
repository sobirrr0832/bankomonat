# Python 3.9 imidjidan foydalanamiz
FROM python:3.9-slim

# Ishchi katalogni yaratamiz
WORKDIR /app

# Talablar faylini konteynerga nusxalaymiz
COPY requirements.txt /app/

# Talablarni o'rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# Kodekni konteynerga nusxalaymiz
COPY . /app/

# Asosiy skriptni ishga tushiramiz
CMD ["python", "valyuta_omonat_bot.py"]
