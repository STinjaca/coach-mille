
import traceback


try:
    print(0/0)
except Exception as e:
    print(f"{traceback.format_exc()}")
