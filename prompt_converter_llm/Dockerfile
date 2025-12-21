# "slim" variants are smaller and faster to build
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Optimize Build Cache: Copy requirements FIRST
COPY requirements.txt .

# 4. Install dependencies
# --no-cache-dir keeps the image small by removing pip cache files
RUN pip install --no-cache-dir -r requirements.txt

#5. Copy the rest of your application code
COPY . .

# 6. Expose the port your app runs on (Documentation only)
# Standard FastAPI port is 8000
EXPOSE 8000

# 7. Define the command to start your app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]