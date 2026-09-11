import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BACKEND_ROOT)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)