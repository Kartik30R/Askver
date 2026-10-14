import json
import pathlib
import threading
import traceback

from agents.nodes.company_research import company_research_node
from app.utils.serializers import to_primitive

OUTPUT_PATH = pathlib.Path(__file__).resolve().parent / "outputs" / "company_research_node_result.txt"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

state = {
    "target_company": "Microsoft",
    "target_industry": "Software and cloud services",
    "meeting_objective": "Assess strategic priorities, technology investments, and executive risks for a partnership discussion.",
    "dynamic_instructions": [],
    "errors": [],
    "node_statuses": {},
}

container = {}


def run_node():
    try:
        container["result"] = company_research_node(state)
    except Exception:
        container["error"] = traceback.format_exc()


try:
    thread = threading.Thread(target=run_node, daemon=True)
    thread.start()
    thread.join(timeout=180)

    if thread.is_alive():
        payload = "TIMEOUT: company_research_node did not finish within 180 seconds.\n"
    elif "error" in container:
        payload = "ERROR:\n" + container["error"]
    else:
        payload = json.dumps(to_primitive(container.get("result")), indent=2, ensure_ascii=False)

except Exception:
    payload = "UNHANDLED_EXCEPTION:\n" + traceback.format_exc()

OUTPUT_PATH.write_text(payload, encoding="utf-8")
print(str(OUTPUT_PATH))
print(payload[:4000])
