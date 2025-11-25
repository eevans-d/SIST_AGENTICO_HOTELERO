from app.worker import test_task

# Test Celery task
result = test_task.delay('Hello from Celery!')
print(f"Task ID: {result.id}")
print(f"Task state: {result.state}")

# Wait for result (with timeout)
try:
    output = result.get(timeout=10)
    print(f"Task result: {output}")
except Exception as e:
    print(f"Error: {e}")
