"""Initialize the existing MVP without changing its host-only development launcher."""
import runpy
from pathlib import Path
import uvicorn
namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "backend" / "run.py"))
import os
namespace["app"].app.state.tenant_root = Path(os.getenv("FINAGENT_TENANT_ROOT", "/data/tenants"))
uvicorn.run(namespace["app"].app, host="0.0.0.0", port=8000)
