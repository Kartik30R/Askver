import logging
import re
from typing import Any, Dict, List, Optional
from urllib import request
from urllib.parse import quote

import yfinance as yf

logger = logging.getLogger(__name__)

US_EXCHANGES = {
    "AMEX",
    "ASE",
    "BATS",
    "NASDAQ",
    "NMS",
    "NCM",
    "NYSE",
    "OTCBB",
    "OTCQX",
    "OTCMKTS",
    "PNK",
}

SEC_USER_AGENT = "AskVer/1.0 (+support@askver.ai)"


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _normalize_company_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "" or value == "N/A":
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        digits = value.replace(",", "").replace("%", "").strip()

        try:
            return float(digits)
        except ValueError:
            return None

    return None


def _is_us_exchange(exchange: Optional[str]) -> bool:
    if not exchange:
        return False

    normalized = str(exchange).upper().replace(".", "")

    return (
        normalized in US_EXCHANGES
        or normalized in {
            "NASD",
            "NYSEARCA",
            "NYSEAMERICAN",
        }
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_ratio(
    value: Optional[float],
    good_threshold: float,
    medium_threshold: float,
) -> int:
    if value is None or value <= 0:
        return 0

    if value >= good_threshold:
        return 100

    if value >= medium_threshold:
        return 75

    return 50


def _score_growth(value: Optional[float]) -> int:
    if value is None or value <= 0:
        return 0

    if value >= 0.15:
        return 100

    if value >= 0.08:
        return 75

    if value >= 0.03:
        return 60

    return 40


METRIC_WEIGHTS = {
    "revenue_growth": 0.30,
    "gross_margin": 0.20,
    "operating_margin": 0.20,
    "ebitda_margin": 0.15,
    "free_cashflow_margin": 0.15,
}


# ---------------------------------------------------------------------------
# SEC lookup
# ---------------------------------------------------------------------------

def _lookup_sec_company(search_term: str) -> Optional[Dict[str, str]]:
    """
    Check whether the company appears in SEC EDGAR.

    This function only establishes an SEC reference. It does not claim that
    the financial figures themselves were retrieved from an SEC filing.
    """

    term = _normalize_company_name(search_term)

    if not term:
        return None

    encoded = quote(term)

    sec_url = (
        "https://www.sec.gov/cgi-bin/browse-edgar?"
        f"action=getcompany&company={encoded}"
        "&owner=exclude&match=contains&count=10&output=atom"
    )

    try:
        req = request.Request(
            sec_url,
            headers={
                "User-Agent": SEC_USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )

        with request.urlopen(req, timeout=15) as response:
            text = response.read().decode(
                "utf-8",
                errors="ignore",
            )

        if "No matching" in text or "No SEC filings" in text:
            return None

        if "<entry>" in text or "companyinfo" in text.lower():
            return {
                "company_name": term,
                "url": sec_url,
                "source_type": "SEC",
            }

    except Exception as exc:
        logger.warning(
            "SEC lookup failed for %s: %s",
            term,
            exc,
        )

    return None


# ---------------------------------------------------------------------------
# Yahoo Finance company/ticker resolution
# ---------------------------------------------------------------------------

def resolve_company_symbol(
    company_or_ticker: str,
) -> Optional[str]:

    raw = _normalize_company_name(company_or_ticker)

    if not raw:
        return None

    candidate = raw.upper()

    # Possible ticker
    if re.fullmatch(r"[A-Z0-9.\-]{1,10}", candidate):
        try:
            info = yf.Ticker(raw).info or {}

            if info.get("symbol"):
                return str(info["symbol"]).upper()

            return raw.upper()

        except Exception:
            return raw.upper()

    search_queries = [
        raw,
        raw.replace(" INC", "")
           .replace(" CORP", "")
           .replace(" CORPORATION", "")
           .replace(" COMPANY", "")
           .strip(),
        raw.split()[0],
    ]

    seen = set()

    for query in search_queries:

        if not query or query in seen:
            continue

        seen.add(query)

        try:
            search_result = yf.search(
                query,
                max_results=10,
                news=False,
            )

            quotes = (
                search_result.get("quotes", [])
                if isinstance(search_result, dict)
                else []
            )

            for item in quotes:

                symbol = item.get("symbol")
                exchange = (
                    item.get("exchange")
                    or item.get("fullExchangeName")
                )

                if symbol and _is_us_exchange(exchange):
                    return str(symbol).upper()

        except Exception as exc:
            logger.warning(
                "Yahoo Finance lookup failed for %s: %s",
                query,
                exc,
            )

    return None


# ---------------------------------------------------------------------------
# Public-company financial extraction
# ---------------------------------------------------------------------------

def _build_metric_scores(
    info: Dict[str, Any],
) -> Dict[str, Any]:

    total_revenue = _safe_float(
        info.get("totalRevenue")
    )

    revenue_growth = _safe_float(
        info.get("revenueGrowth")
    )

    gross_margin = _safe_float(
        info.get("grossMargins")
    )

    operating_margin = _safe_float(
        info.get("operatingMargins")
    )

    ebitda = _safe_float(
        info.get("ebitda")
    )

    free_cashflow = _safe_float(
        info.get("freeCashflow")
    )

    market_cap = _safe_float(
        info.get("marketCap")
    )

    ebitda_margin = None

    if total_revenue and total_revenue > 0 and ebitda is not None:
        ebitda_margin = ebitda / total_revenue

    free_cashflow_margin = None

    if (
        total_revenue
        and total_revenue > 0
        and free_cashflow is not None
    ):
        free_cashflow_margin = (
            free_cashflow / total_revenue
        )

    metric_definitions = [
        (
            "revenue_growth",
            revenue_growth,
            _score_growth,
        ),
        (
            "gross_margin",
            gross_margin,
            lambda v: _score_ratio(v, 0.45, 0.30),
        ),
        (
            "operating_margin",
            operating_margin,
            lambda v: _score_ratio(v, 0.20, 0.12),
        ),
        (
            "ebitda_margin",
            ebitda_margin,
            lambda v: _score_ratio(v, 0.18, 0.10),
        ),
        (
            "free_cashflow_margin",
            free_cashflow_margin,
            lambda v: _score_ratio(v, 0.12, 0.05),
        ),
    ]

    metric_scores = {}

    weighted_total = 0.0
    weight_total = 0.0

    for metric_name, value, score_fn in metric_definitions:

        available = value is not None

        score = score_fn(value) if available else 0

        metric_scores[metric_name] = {
            "metric_name": metric_name,
            "value": value,
            "score": score,
            "status": (
                "available"
                if available
                else "unavailable"
            ),
            "source_type": "yfinance",
            "confidence": "high" if available else "none",
        }

        if available:
            weight = METRIC_WEIGHTS[metric_name]

            weighted_total += score * weight
            weight_total += weight

    overall_score = (
        round(weighted_total / weight_total, 1)
        if weight_total
        else 0
    )

    coverage = (
        round(
            (weight_total / sum(METRIC_WEIGHTS.values()))
            * 100
        )
        if weight_total
        else 0
    )

    return {
        "overall_score": int(round(overall_score)),
        "score_coverage": coverage,
        "metric_scores": metric_scores,
        "market_cap": market_cap,
        "currency": info.get("currency", "USD"),
    }


# ---------------------------------------------------------------------------
# Private-company web evidence
# ---------------------------------------------------------------------------

def build_private_company_search_queries(
    company_name: str,
) -> List[str]:
    """
    Generates search queries for discovering financial information
    about private companies.

    These queries should be passed to your web-search provider.
    """

    company = _normalize_company_name(company_name)

    return [
        f'"{company}" revenue',
        f'"{company}" annual revenue',
        f'"{company}" revenue 2025',
        f'"{company}" revenue 2026',
        f'"{company}" EBITDA',
        f'"{company}" profit',
        f'"{company}" earnings',
        f'"{company}" financial results',
        f'"{company}" annual report',
        f'"{company}" valuation',
        f'"{company}" funding',
        f'"{company}" financing',
        f'"{company}" "revenue growth"',
        f'"{company}" CEO revenue interview',
        f'"{company}" founder revenue interview',
        f'"{company}" financials',
    ]


# ---------------------------------------------------------------------------
# Financial evidence model
# ---------------------------------------------------------------------------

def make_financial_evidence(
    metric_name: str,
    value: Optional[float],
    *,
    currency: Optional[str] = None,
    period: Optional[str] = None,
    source_url: Optional[str] = None,
    source_title: Optional[str] = None,
    source_type: str = "unknown",
    confidence: str = "low",
    notes: Optional[str] = None,
) -> Dict[str, Any]:

    return {
        "metric_name": metric_name,
        "value": value,
        "currency": currency,
        "period": period,
        "source_url": source_url,
        "source_title": source_title,
        "source_type": source_type,
        "confidence": confidence,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Evidence confidence
# ---------------------------------------------------------------------------

SOURCE_CONFIDENCE = {
    "audited_filing": "very_high",
    "regulatory_filing": "very_high",
    "company_reported": "high",
    "financing_transaction": "high",
    "executive_interview": "medium",
    "reputable_news": "medium",
    "industry_report": "low",
    "analyst_estimate": "low",
    "unverified": "very_low",
}


def confidence_score(confidence: str) -> float:
    return {
        "very_high": 1.00,
        "high": 0.85,
        "medium": 0.65,
        "low": 0.40,
        "very_low": 0.15,
        "none": 0.00,
    }.get(confidence, 0.0)


# ---------------------------------------------------------------------------
# Private-company scoring
# ---------------------------------------------------------------------------

def score_private_company_metrics(
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:

    metric_values = {}

    for item in evidence:

        metric_name = item.get("metric_name")
        value = item.get("value")

        if metric_name and value is not None:
            metric_values[metric_name] = item

    revenue_growth = metric_values.get(
        "revenue_growth"
    )

    gross_margin = metric_values.get(
        "gross_margin"
    )

    operating_margin = metric_values.get(
        "operating_margin"
    )

    ebitda_margin = metric_values.get(
        "ebitda_margin"
    )

    free_cashflow_margin = metric_values.get(
        "free_cashflow_margin"
    )

    definitions = [
        (
            "revenue_growth",
            revenue_growth,
            _score_growth,
        ),
        (
            "gross_margin",
            gross_margin,
            lambda v: _score_ratio(v, 0.45, 0.30),
        ),
        (
            "operating_margin",
            operating_margin,
            lambda v: _score_ratio(v, 0.20, 0.12),
        ),
        (
            "ebitda_margin",
            ebitda_margin,
            lambda v: _score_ratio(v, 0.18, 0.10),
        ),
        (
            "free_cashflow_margin",
            free_cashflow_margin,
            lambda v: _score_ratio(v, 0.12, 0.05),
        ),
    ]

    weighted_total = 0.0
    weight_total = 0.0

    metric_scores = {}

    for metric_name, evidence_item, score_fn in definitions:

        if not evidence_item:
            metric_scores[metric_name] = {
                "metric_name": metric_name,
                "status": "unavailable",
                "score": None,
            }
            continue

        value = evidence_item["value"]

        raw_score = score_fn(value)

        confidence = confidence_score(
            evidence_item.get("confidence", "low")
        )

        # Confidence-adjusted contribution.
        adjusted_score = raw_score * confidence

        weight = METRIC_WEIGHTS[metric_name]

        weighted_total += (
            adjusted_score * weight
        )

        weight_total += weight

        metric_scores[metric_name] = {
            "metric_name": metric_name,
            "value": value,
            "raw_score": raw_score,
            "confidence": evidence_item.get(
                "confidence"
            ),
            "source_type": evidence_item.get(
                "source_type"
            ),
            "source_url": evidence_item.get(
                "source_url"
            ),
            "status": "available",
        }

    overall_score = (
        round(
            weighted_total / weight_total,
            1,
        )
        if weight_total
        else 0
    )

    coverage = (
        round(
            (
                weight_total
                / sum(METRIC_WEIGHTS.values())
            )
            * 100
        )
        if weight_total
        else 0
    )

    available_confidences = [
        confidence_score(
            item.get("confidence", "low")
        )
        for item in evidence
        if item.get("value") is not None
    ]

    average_confidence = (
        round(
            sum(available_confidences)
            / len(available_confidences),
            2,
        )
        if available_confidences
        else 0
    )

    return {
        "overall_score": int(round(overall_score)),
        "score_coverage": coverage,
        "average_evidence_confidence": average_confidence,
        "metric_scores": metric_scores,
    }


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def _build_summary(
    company_name: str,
    status: str,
    details: Dict[str, Any],
) -> str:

    score = details.get(
        "overall_score",
        0,
    )

    coverage = details.get(
        "score_coverage",
        0,
    )

    if status == "private":

        return (
            f"{company_name} appears to be a private company. "
            f"Publicly available financial evidence supports a "
            f"financial quality score of {score}/100, with "
            f"{coverage}% coverage of the scoring framework. "
            "Private-company financial information may come from "
            "company statements, executive interviews, financing "
            "reports, or reputable third-party sources and may not "
            "be audited."
        )

    return (
        f"{company_name} has a U.S.-listed public profile with "
        f"a financial quality score of {score}/100. "
        f"The scoring framework has {coverage}% data coverage."
    )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def get_company_financials(
    company_or_ticker: str,
    private_evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:

    query = _normalize_company_name(
        company_or_ticker
    )

    if not query:
        return {
            "company_name": "",
            "symbol": None,
            "status": "unknown",
            "availability": "unavailable",
            "financial_score": {
                "overall_score": 0,
            },
            "metric_scores": {},
            "ai_summary": (
                "No company name or ticker was provided."
            ),
        }

    # ---------------------------------------------------------
    # 1. Try public-company resolution first
    # ---------------------------------------------------------

    resolved_symbol = resolve_company_symbol(query)

    if resolved_symbol:

        try:
            ticker = yf.Ticker(
                resolved_symbol
            )

            info = ticker.info or {}

            company_name = (
                info.get("longName")
                or info.get("shortName")
                or query
            )

            details = _build_metric_scores(
                info
            )

            details.update({
                "company_name": company_name,
                "symbol": resolved_symbol,
                "status": "listed",
                "market": "USA",
                "availability": "available",
                "data_source": "yfinance",
                "financial_score": {
                    "overall_score": details[
                        "overall_score"
                    ],
                    "score_coverage": details[
                        "score_coverage"
                    ],
                    "score_detail": (
                        "Weighted score using revenue "
                        "growth, gross margin, operating "
                        "margin, EBITDA margin, and free "
                        "cash flow margin."
                    ),
                },
            })

            details["ai_summary"] = _build_summary(
                company_name,
                "listed",
                details,
            )

            return details

        except Exception as exc:

            logger.error(
                "Public financial lookup failed for %s: %s",
                query,
                exc,
            )

    # ---------------------------------------------------------
    # 2. SEC reference
    # ---------------------------------------------------------

    sec_reference = _lookup_sec_company(
        query
    )

    # ---------------------------------------------------------
    # 3. Private-company evidence
    # ---------------------------------------------------------

    if private_evidence:

        scoring = score_private_company_metrics(
            private_evidence
        )

        result = {
            "company_name": query,
            "symbol": None,
            "status": "private",
            "market": "USA",
            "availability": "partial",
            "data_source": "web_evidence",
            "financial_score": {
                "overall_score": scoring[
                    "overall_score"
                ],
                "score_coverage": scoring[
                    "score_coverage"
                ],
                "average_evidence_confidence": scoring[
                    "average_evidence_confidence"
                ],
            },
            "metric_scores": scoring[
                "metric_scores"
            ],
            "financial_evidence": private_evidence,
            "search_queries": build_private_company_search_queries(
                query
            ),
            "sec_reference": sec_reference,
        }

        result["ai_summary"] = _build_summary(
            query,
            "private",
            result["financial_score"],
        )

        return result

    # ---------------------------------------------------------
    # 4. Nothing found
    # ---------------------------------------------------------

    return {
        "company_name": query,
        "symbol": None,
        "status": (
            "private_or_unverified"
        ),
        "market": "USA",
        "availability": "unavailable",
        "data_source": (
            "SEC"
            if sec_reference
            else "unavailable"
        ),
        "financial_score": {
            "overall_score": 0,
            "score_coverage": 0,
        },
        "metric_scores": {},
        "financial_evidence": [],
        "search_queries": build_private_company_search_queries(
            query
        ),
        "sec_reference": sec_reference,
        "ai_summary": (
            f"No sufficiently reliable financial "
            f"information was found for {query}. "
            "The company may be private, or available "
            "financial information could not be verified. "
            "No financial figures were fabricated."
        ),
    }
