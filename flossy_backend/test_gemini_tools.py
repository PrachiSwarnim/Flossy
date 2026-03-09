import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
from google.genai import Client, types

client = Client()

gemini_tools = [{
    "function_declarations": [
        {
            "name": "get_appointments",
            "description": "Fetch a list of appointments for a specific date.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date_str": {"type": "STRING", "description": "YYYY-MM-DD or today"}
                },
                "required": ["date_str"]
            }
        }
    ]
}]

def test():
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config={
                "tools": gemini_tools,
                "temperature": 0.4
            }
        )
        response = chat.send_message("What are my appts today?")
        print("Function calls:", response.function_calls)
        
        if response.function_calls:
            responses = []
            for fc in response.function_calls:
                responses.append({"function_response": {"name": fc.name, "response": {"result": "You have 3 appointments."}}})
            
            final_resp = chat.send_message(responses)
            print("Final resp:", final_resp.text)
            
    except Exception as e:
        print("Error:", e)

test()
