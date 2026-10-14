import json
import traceback

from app.core.config import settings

from app.services.llm_provider import get_llm
from agents.nodes.company_research import company_research_node
from agents.state import DealIntelligenceState
from app.utils.serializers import to_primitive


state = {
    'target_company': 'Microsoft',
    'target_industry': 'Software and cloud services',
    'dynamic_instructions': [],
    'errors': [],
    'node_statuses': {},
}

try:
    print('=== RUN COMPANY_RESEARCH START ===')
    # 1) Try building LLM first to surface import/config errors quickly
    try:
        print('--- Building LLM ---')
        llm = get_llm(model=settings.LLM_MODEL, provider=settings.LLM_PROVIDER, temperature=0.1)
        print('LLM built:', type(llm).__name__)
    except Exception as e:
        print('LLM build error:', str(e))

    # 2) Run the node in a thread with timeout to avoid indefinite hangs
    import threading

    container = {}

    def run_node():
        try:
            container['result'] = company_research_node(state)
        except Exception as e:
            container['error'] = str(e)

    t = threading.Thread(target=run_node, daemon=True)
    t.start()
    t.join(timeout=60)

    if t.is_alive():
        print('NODE TIMEOUT: company_research_node did not finish within 60s')
    else:
        if 'error' in container:
            print('NODE ERROR:', container['error'])
        else:
            print('=== NODE RESULT ===')
            serial = to_primitive(container.get('result'))
            print(json.dumps(serial, indent=2, ensure_ascii=False))
    print('=== RUN COMPANY_RESEARCH END ===')
except Exception:
    traceback.print_exc()
    raise
