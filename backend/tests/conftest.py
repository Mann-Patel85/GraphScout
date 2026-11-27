"""Test configuration: always run offline.

Blank provider keys are set *before* anything calls ``load_dotenv()``; python-dotenv
never overrides variables that already exist, so a developer's ``backend/.env``
cannot make the test suite call (and bill) a real LLM API.
"""

import os

for _var in ("OPENAI_API_KEY", "GROQ_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "NEO4J_URI", "GRAPH_BACKEND"):
    os.environ[_var] = ""
