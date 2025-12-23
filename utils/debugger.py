import inspect
import traceback

def debug_wrap(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print("\n" + "="*60)
            print(f"🔥 ERROR IN FUNCTION: {func.__name__}")
            print("="*60)
            print("📌 Error:", str(e))
            print("📌 TYPE:", type(e))

            frame = inspect.trace()[-1]
            print(f"📍 TRACE LOCATION: File={frame.filename}, Line={frame.lineno}")

            print("\n--- Function Arguments & Types ---")
            for i, a in enumerate(args):
                print(f"arg[{i}] = {a}   TYPE → {type(a)}")

            for k, v in kwargs.items():
                print(f"{k} = {v}   TYPE → {type(v)}")

            print("\n--- FULL TRACEBACK ---")
            traceback.print_exc()
            print("="*60 + "\n")

            raise
    return wrapper
