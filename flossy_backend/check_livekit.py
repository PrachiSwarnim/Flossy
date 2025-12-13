try:
    import livekit.agents
    print(f"livekit.agents version: {getattr(livekit.agents, '__version__', 'unknown')}")
    from livekit.agents import llm
    print("llm module found")
    
    if hasattr(llm, 'FunctionContext'):
        print("FunctionContext found directly in llm")
    else:
        print("FunctionContext NOT found directly in llm")
        
    try:
        from livekit.agents.llm import function_context
        print("function_context submodule found")
        if hasattr(function_context, 'FunctionContext'):
            print("FunctionContext found in function_context submodule")
        if hasattr(function_context, 'ai_callable'):
            print("ai_callable found in function_context submodule")
    except ImportError as e:
        print(f"function_context submodule NOT found: {e}")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
