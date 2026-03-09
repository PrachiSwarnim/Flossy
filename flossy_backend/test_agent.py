import requests

res = requests.post(
    "http://localhost:8000/api/v1/ai/chat", 
    json={"message": "Who are my patients for today?", "context": "dentist_dashboard"},
    headers={"Authorization": "Bearer TEST_TOKEN"}
)

print(res.status_code)
print(res.text)
