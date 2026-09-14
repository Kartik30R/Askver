import logging
from typing import Dict, Any

from app.agents.state import DealIntelligenceState
from app.agents.tools.financial_tool import get_company_financials

logger = logging.getLogger(__name__)


def financial_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent: Financial Intelligence Agent

    Fetches financial data for the target company, evaluates the company's
    financial metrics, and returns a normalized financial intelligence payload.
    """

    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")

    logger.info(
        f"Starting Financial Intelligence Node for: "
        f"{target_company} ({target_industry})"
    )

    # =========================================================================
    # 1. FINANCIAL DATA EXTRACTION
    # =========================================================================

    try:
        logger.info(
            f"Fetching financial data for ticker/company: {target_company}"
        )

        financial_result = get_company_financials(target_company)

        metric_scores = financial_result.get("metric_scores", {})
        metric_entries = []

        if isinstance(metric_scores, dict):
            for metric_name, metric_payload in metric_scores.items():
                if isinstance(metric_payload, dict):
                    metric_entries.append({
                        "metric_name": metric_name,
                        **metric_payload
                    })

        # =========================================================================
        # 2. NORMALIZE FINANCIAL INTELLIGENCE OUTPUT
        # =========================================================================

        payload = {
            "company_name": financial_result.get(
                "company_name",
                target_company
            ),
            "symbol": financial_result.get("symbol"),
            "status": financial_result.get(
                "status",
                "not_listed"
            ),
            "market": financial_result.get(
                "market",
                "USA"
            ),
            "availability": financial_result.get(
                "availability",
                "unavailable"
            ),
            "data_source": financial_result.get(
                "data_source",
                "unavailable"
            ),
            "financial_score": financial_result.get(
                "financial_score",
                {
                    "overall_score": 0,
                    "score_detail": "unavailable"
                }
            ),
            "metric_scores": metric_entries,
            "ai_summary": financial_result.get(
                "ai_summary",
                "Financial information is unavailable."
            ),
            "sec_reference": financial_result.get("sec_reference"),
        }

        logger.info(
            f"Successfully completed Financial Intelligence Node "
            f"for {target_company}"
        )

        # =========================================================================
        # 3. RETURN UPDATED LANGGRAPH STATE
        # =========================================================================

        return {
            "financial_intelligence": payload,
            "node_statuses": {
                "financial_intelligence": "COMPLETED"
            }
        }

    except Exception as e:
        logger.error(
            f"Error in Financial Intelligence Node: {str(e)}",
            exc_info=True
        )

        return {
            "errors": [
                f"Financial Intelligence Node failed: {str(e)}"
            ],
            "node_statuses": {
                "financial_intelligence": "FAILED"
            }
        }
