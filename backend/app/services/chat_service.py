
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.deal_document_repository import DealDocumentRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.schemas.chat import ApproveEditResponse, ChatQueryResponse, ProposeEditResponse
from app.services.llm_provider import get_llm
from app.services.vector_service import query_client_deal_docs

logger = logging.getLogger(__name__)

ACTIVE_EDIT_PROPOSALS: Dict[str, Dict[str, Any]] = {}


class ChatService:
    """Chat + revision layer on top of the deal report and workflow state."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DealDocumentRepository(db)
        self.intel_repo = DealIntelligenceRepository(db)

    async def answer_deal_query(self, deal_id: UUID, question: str) -> ChatQueryResponse:
        """Answer from the latest full workflow state, with report markdown as a supporting artifact."""
        state = await self._get_latest_state(deal_id)
        report_text = self._extract_report_text(state)
        citations = self._collect_citations(state)

        normalized = (question or '').strip()
        if not normalized:
            raise ValueError("A question is required to chat with the deal assistant.")

        if not state:
            answer = (
                "The deal state is not ready yet. Run the workflow or generate the brief first, "
                "then ask me questions about the current deal and its analysis."
            )
        else:
            full_state_context = self._stringify_state(state)
            prompt = self._build_grounding_prompt(report_text, full_state_context, normalized)
            try:
                answer = await self._call_llm(prompt)
            except Exception:
                question_lower = normalized.lower()
                if "financial" in question_lower or "budget" in question_lower or "revenue" in question_lower:
                    answer = self._extract_section(report_text, "Financial")
                elif "cxo" in question_lower or "brief" in question_lower or "summary" in question_lower:
                    answer = self._extract_section(report_text, "Executive")
                elif "pain" in question_lower or "priority" in question_lower:
                    answer = self._extract_section(report_text, "Pain")
                else:
                    answer = self._summarize_report(report_text, normalized)

        return ChatQueryResponse(
            deal_id=str(deal_id),
            answer=answer,
            citations=citations,
        )

    async def propose_text_edit(
        self,
        deal_id: UUID,
        instruction: str,
        section: Optional[str] = None,
        current_text: Optional[str] = None,
    ) -> ProposeEditResponse:
        """Generate a revised text proposal for a section or the full report."""
        state = await self._get_latest_state(deal_id)
        source_text = current_text or self._extract_section_text_for_edit(state, section)

        if not source_text:
            source_text = self._extract_report_text(state) or "No report content available yet."

        revised = await self._rewrite_text(source_text, instruction, state)
        proposal_id = uuid.uuid4()
        payload = {
            "deal_id": str(deal_id),
            "section": section,
            "current_text": source_text,
            "proposed_text": revised,
        }
        ACTIVE_EDIT_PROPOSALS[str(proposal_id)] = payload
        return ProposeEditResponse(
            deal_id=str(deal_id),
            section=section,
            proposed_diff_id=proposal_id,
            current_text=source_text,
            proposed_text=revised,
            status="proposal_created",
        )

    async def approve_text_edit(
        self,
        deal_id: UUID,
        proposed_diff_id: UUID,
        approved: bool = True,
    ) -> ApproveEditResponse:
        """Accept or reject a previously generated proposal, returning the decision outcome."""
        if not proposed_diff_id:
            raise ValueError("A proposal ID is required to approve or reject an edit.")

        proposal = ACTIVE_EDIT_PROPOSALS.get(str(proposed_diff_id))
        if approved and proposal:
            latest_snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
            if not latest_snapshot:
                raise ValueError("No active deal snapshot was found to update.")

            updated_state = dict(latest_snapshot.snapshot_data or {})
            proposed_text = proposal.get("proposed_text") or updated_state.get("markdown_export")
            target_section = proposal.get("section") or "general"

            if target_section == "general":
                updated_state["markdown_export"] = proposed_text
                updated_state["final_report"] = proposed_text
                updated_state["report_markdown"] = proposed_text
            else:
                updated_state[target_section] = proposed_text
                if target_section == "cxo_executive_brief":
                    updated_state["markdown_export"] = proposed_text
                    updated_state["final_report"] = proposed_text
                elif target_section == "financial_intelligence":
                    updated_state["financial_intelligence"] = {"summary": proposed_text}

            await self.intel_repo.save_intelligence_snapshot(
                deal_id=deal_id,
                thread_id=latest_snapshot.thread_id,
                current_step=latest_snapshot.current_step or "APPROVED_EDIT",
                snapshot_data=updated_state,
            )
            ACTIVE_EDIT_PROPOSALS.pop(str(proposed_diff_id), None)

        if proposal and not approved:
            ACTIVE_EDIT_PROPOSALS.pop(str(proposed_diff_id), None)

        decision = "approved" if approved else "rejected"
        return ApproveEditResponse(
            deal_id=str(deal_id),
            proposed_diff_id=proposed_diff_id,
            approved=approved,
            status="edit_approval_processed",
            message=f"Proposal {proposed_diff_id} was {decision} for deal {deal_id}.",
        )

    async def _get_latest_state(self, deal_id: UUID) -> Dict[str, Any]:
        snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        return snapshot.snapshot_data if snapshot else {}
    def _extract_report_text(self, state: Dict[str, Any]) -> str:
        if not state:
            return ""
        return str(state.get("markdown_export") or state.get("cxo_executive_brief") or state.get("final_report") or "")

    def _collect_citations(self, state: Dict[str, Any]) -> List[str]:
        citations: List[str] = []
        if not state:
            return citations
        for key in ("matched_internal_assets", "service_mappings"):
            values = state.get(key) or []
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        name = item.get("asset_name") or item.get("title") or item.get("client_need")
                        if name:
                            citations.append(str(name))
        return list(dict.fromkeys(citations))

    def _extract_section(self, report_text: str, heading: str) -> str:
        normalized = report_text.replace("\r", "")
        start = normalized.lower().find(f"## {heading.lower()}")
        if start == -1:
            start = normalized.lower().find(heading.lower())
        if start == -1:
            return report_text[:600]
        end = normalized.find("\n---", start)
        if end == -1:
            end = len(normalized)
        return normalized[start:end][:1200]

    def _extract_section_text_for_edit(self, state: Dict[str, Any], section: Optional[str]) -> str:
        if not section:
            return self._extract_report_text(state)

        if isinstance(state.get(section), dict):
            return str(state.get(section))
        if section == "cxo_executive_brief":
            return str(state.get("cxo_executive_brief") or "")
        if section == "financial_intelligence":
            return str(state.get("financial_intelligence") or "")
        return self._extract_report_text(state)

    def _summarize_report(self, report_text: str, question: str) -> str:
        preview = report_text[:800].strip()
        return (
            f"Based on the current report, the key point is: {preview[:400]}\n\n"
            f"If you want a tighter answer for this section, ask specifically about financials, CXO brief, priorities, or service mapping."
        )

    def _stringify_state(self, state: Dict[str, Any]) -> str:
        try:
            return json.dumps(state, default=str, ensure_ascii=False, sort_keys=True)[:20000]
        except Exception:
            return str(state)[:20000]

    def _build_grounding_prompt(self, report_text: str, full_state_context: str, question: str) -> str:
        return (
            "You are an executive advisory assistant. Use the full deal state and the generated report as your context. "
            "Answer based on the actual workflow outputs and report contents. Do not invent missing facts. "
            "If a fact is unclear, say so explicitly and provide the best evidence-based answer available.\n\n"
            f"Deal state snapshot:\n{full_state_context[:20000]}\n\n"
            f"Generated report:\n{report_text[:12000]}\n\n"
            f"User question: {question}\n\n"
            "Answer as a concise but highly informed strategic advisor."
        )

    async def _rewrite_text(self, source_text: str, instruction: str, state: Optional[Dict[str, Any]] = None) -> str:
        context = self._stringify_state(state or {}) if state else source_text
        prompt = (
            "You are an expert strategic advisor. Rewrite the provided text to match the user instruction while preserving the substance. "
            "Use the deal context when needed to keep the language accurate and executive-ready.\n\n"
            f"Instruction: {instruction}\n\n"
            f"Context:\n{context[:15000]}\n\n"
            f"Original text:\n{source_text}\n\n"
            "Return only the revised text."
        )
        try:
            return await self._call_llm(prompt)
        except Exception:
            return "Updated draft:\n\n" + (source_text[:1200] or "No content available")

    async def _query_vector_store(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        logger.info(f"Querying vector collection '{collection_name}' for query: '{query_text}'")
        deal_id = collection_name.replace("deal_", "")
        return query_client_deal_docs(deal_id=deal_id, query=query_text, top_k=top_k)

    async def _call_llm(self, prompt: str) -> str:
        try:
            llm = get_llm(
                model=settings.LLM_MODEL,
                provider=settings.LLM_PROVIDER,
                temperature=0.2,
            )
            response = llm.invoke(prompt)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                return "\n".join(
                    str(part.get("text") if isinstance(part, dict) else part)
                    for part in content
                )
            text = str(content).strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("LLM chat generation failed for grounded response: %s", exc)

        return "I could not generate a fresh answer from the configured model, so I’m using the latest report context instead."