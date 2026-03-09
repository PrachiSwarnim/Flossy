import asyncio
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.api.v1.ai.agent_tools import execute_tool, TOOLS_SCHEMA
from app.services.llm_client import groq_client

async def test_groq():
    system_context = """You are FlossyAI, an intelligent dental practice assistant for Dr. Prachi at Smile Artists Dental Studio.
    You help with:
    - Summarizing patient histories and appointments
    - Generating prescription templates
    - Providing clinical suggestions
    - Answering dental practice management questions
    - Patient follow-up reminders
    Keep responses concise (max 3 sentences) and professional."""
    
    message = "ALL APPTS OF TODAY TELL"
    
    print("Sending to Groq...")
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_context},
            {"role": "user", "content": message}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.4,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",
    )
    
    response_msg = chat_completion.choices[0].message
    tool_calls = response_msg.tool_calls
    
    if tool_calls:
        print(f"🔧 FlossyAI is calling {len(tool_calls)} tools!")
        for tool_call in tool_calls:
            print("Tool called:", tool_call.function.name, tool_call.function.arguments)
    else:
        print("NO TOOLS CALLED. Response:", response_msg.content)

if __name__ == "__main__":
    asyncio.run(test_groq())
