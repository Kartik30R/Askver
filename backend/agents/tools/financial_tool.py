import json
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

METRIC_WEIGHTS = {
    "revenue_growth": 0.30,
    "gross_margin": 0.20,
    "operating_margin": 0.20,
    "ebitda_margin": 0.15,
    "free_cashflow_margin": 0.15,
}

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


# Yahoo ticker suffixes for non-US listings (NSE/BSE, London, Frankfurt, ...)
GLOBAL_SUFFIXES = (
    ".NS", ".BO", ".L", ".DE", ".PA", ".AS", ".SW", ".TO", ".HK", ".T", ".AX", ".SI",
)


def _is_acceptable_symbol(symbol: str, exchange: Optional[str]) -> bool:
    """US listings plus well-known global exchanges (India, UK, EU, ...)."""
    if _is_us_exchange(exchange):
        return True
    return str(symbol).upper().endswith(GLOBAL_SUFFIXES)


def classify_market_cap(market_cap: Optional[float]) -> str:
    if not market_cap:
        return "Unknown"
    if market_cap >= 200_000_000_000:  # > $200B
        return "Mega Cap"
    elif market_cap >= 10_000_000_000:  # $10B - $200B
        return "Large Cap"
    elif market_cap >= 2_000_000_000:   # $2B - $10B
        return "Mid Cap"
    elif market_cap >= 300_000_000:     # $300M - $2B
        return "Small Cap"
    else:
        return "Micro Cap"


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

def _symbol_has_quote(symbol: str) -> bool:
    """True only if Yahoo actually knows this symbol (has a live price)."""
    try:
        t = yf.Ticker(symbol)
        try:
            price = t.fast_info.get("last_price") or t.fast_info.get("lastPrice")
            if price:
                return True
        except Exception:
            pass
        info = t.info or {}
        return bool(
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("marketCap")
        )
    except Exception:
        return False


def _search_quotes(query: str) -> List[Dict[str, Any]]:
    """Search Yahoo for symbols. Works across yfinance versions, then falls back to the raw HTTP endpoint."""
    # yfinance >= 0.2.5x: yf.Search(...).quotes
    try:
        if hasattr(yf, "Search"):
            quotes = yf.Search(query, max_results=10, news_count=0).quotes
            if quotes:
                return list(quotes)
    except Exception as exc:
        logger.warning("yf.Search failed for %s: %s", query, exc)

    # Older/other builds: yf.search(...)
    try:
        if hasattr(yf, "search"):
            res = yf.search(query, max_results=10, news=False)
            quotes = res.get("quotes", []) if isinstance(res, dict) else []
            if quotes:
                return list(quotes)
    except Exception as exc:
        logger.warning("yf.search failed for %s: %s", query, exc)

    # Last resort: Yahoo's public search endpoint
    try:
        url = (
            "https://query2.finance.yahoo.com/v1/finance/search?"
            f"q={quote(query)}&quotesCount=10&newsCount=0"
        )
        req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8", errors="ignore")).get("quotes", [])
    except Exception as exc:
        logger.warning("Yahoo search endpoint failed for %s: %s", query, exc)

    return []


def _resolve_by_name(raw: str) -> Optional[str]:
    cleaned = re.sub(
        r"\b(inc|corp|corporation|company|co|ltd|limited|plc|llc)\b\.?",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")

    seen = set()
    for query in (raw, cleaned):
        if not query or query.lower() in seen:
            continue
        seen.add(query.lower())

        for item in _search_quotes(query):
            symbol = item.get("symbol")
            exchange = item.get("exchange") or item.get("exchDisp") or item.get("fullExchangeName")
            quote_type = str(item.get("quoteType", "EQUITY")).upper()

            if not symbol or quote_type not in {"EQUITY", ""}:
                continue
            if _is_acceptable_symbol(symbol, exchange):
                return str(symbol).upper()

    return None


def resolve_company_symbol(
    company_or_ticker: str,
) -> Optional[str]:
    """
    Resolve a company name OR ticker to a verified Yahoo symbol.

    Bare names like "Microsoft" match the ticker regex, so a regex alone is not
    enough: an input is only treated as a ticker if it looks like one
    (UPPERCASE or contains . / -) AND Yahoo returns a real quote for it.
    Everything else goes through name search first.
    """
    raw = _normalize_company_name(company_or_ticker)

    if not raw:
        return None

    looks_like_ticker = bool(
        re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", raw)
        and (raw.isupper() or any(ch in raw for ch in ".-") or any(ch.isdigit() for ch in raw))
    )

    # 1. Explicit-looking ticker (MSFT, RELIANCE.NS, BRK-B) - verify it exists
    if looks_like_ticker and _symbol_has_quote(raw.upper()):
        return raw.upper()

    # 2. Company name search (Microsoft -> MSFT)
    by_name = _resolve_by_name(raw)
    if by_name:
        return by_name

    # 3. Short mixed-case input that might still be a ticker (e.g. "Aapl")
    if re.fullmatch(r"[A-Za-z]{1,5}", raw) and _symbol_has_quote(raw.upper()):
        return raw.upper()

    return None


# ---------------------------------------------------------------------------
# Public-company financial extraction
# ---------------------------------------------------------------------------

def _build_metric_scores(
    info: Dict[str, Any],
) -> Dict[str, Any]:

    total_revenue = _safe_float(info.get("totalRevenue"))
    revenue_growth = _safe_float(info.get("revenueGrowth"))
    gross_margin = _safe_float(info.get("grossMargins"))
    operating_margin = _safe_float(info.get("operatingMargins"))
    ebitda = _safe_float(info.get("ebitda"))
    free_cashflow = _safe_float(info.get("freeCashflow"))
    market_cap = _safe_float(info.get("marketCap"))

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
            "status": "available" if available else "unavailable",
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
# Private-company web evidence & modelling
# ---------------------------------------------------------------------------

def build_private_company_search_queries(
    company_name: str,
) -> List[str]:
    """
    Generates search queries for discovering financial information
    about private companies.
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


def score_private_company_metrics(
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:

    metric_values = {}

    for item in evidence:
        metric_name = item.get("metric_name")
        value = item.get("value")
        if metric_name and value is not None:
            metric_values[metric_name] = item

    revenue_growth = metric_values.get("revenue_growth")
    gross_margin = metric_values.get("gross_margin")
    operating_margin = metric_values.get("operating_margin")
    ebitda_margin = metric_values.get("ebitda_margin")
    free_cashflow_margin = metric_values.get("free_cashflow_margin")

    definitions = [
        ("revenue_growth", revenue_growth, _score_growth),
        ("gross_margin", gross_margin, lambda v: _score_ratio(v, 0.45, 0.30)),
        ("operating_margin", operating_margin, lambda v: _score_ratio(v, 0.20, 0.12)),
        ("ebitda_margin", ebitda_margin, lambda v: _score_ratio(v, 0.18, 0.10)),
        ("free_cashflow_margin", free_cashflow_margin, lambda v: _score_ratio(v, 0.12, 0.05)),
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
        confidence = confidence_score(evidence_item.get("confidence", "low"))

        # Confidence-adjusted contribution
        adjusted_score = raw_score * confidence
        weight = METRIC_WEIGHTS[metric_name]
        
        weighted_total += adjusted_score * weight
        weight_total += weight

        metric_scores[metric_name] = {
            "metric_name": metric_name,
            "value": value,
            "raw_score": raw_score,
            "confidence": evidence_item.get("confidence"),
            "source_type": evidence_item.get("source_type"),
            "source_url": evidence_item.get("source_url"),
            "status": "available",
        }

    overall_score = round(weighted_total / weight_total, 1) if weight_total else 0
    coverage = round((weight_total / sum(METRIC_WEIGHTS.values())) * 100) if weight_total else 0

    available_confidences = [
        confidence_score(item.get("confidence", "low"))
        for item in evidence
        if item.get("value") is not None
    ]

    average_confidence = (
        round(sum(available_confidences) / len(available_confidences), 2)
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
    market: Optional[str] = None,
) -> str:

    score = details.get("overall_score", 0)
    coverage = details.get("score_coverage", 0)
    market_label = market or "public market"

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
        f"{company_name} has a public listing on {market_label} with "
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
    """
    Retrieves and scores financial information for a given company or ticker.
    Returns unified metrics and scoring regardless of public/private status.
    """
    query = _normalize_company_name(company_or_ticker)

    if not query:
        return {
            "company_name": "",
            "symbol": None,
            "status": "unknown",
            "market_cap": None,
            "market_cap_category": "Unknown",
            "raw_metrics": {},
            "availability": "unavailable",
            "financial_score": {"overall_score": 0},
            "metric_scores": {},
            "ai_summary": "No company name or ticker was provided.",
        }

    # ---------------------------------------------------------
    # 1. Try public-company resolution first
    # ---------------------------------------------------------
    resolved_symbol = resolve_company_symbol(query)

    if resolved_symbol:
        try:
            ticker = yf.Ticker(resolved_symbol)
            info = ticker.info or {}

            company_name = info.get("longName") or info.get("shortName") or query
            market_cap = _safe_float(info.get("marketCap"))
            market_name = (info.get("exchange") or info.get("fullExchangeName") or info.get("market") or "Public market").strip()

            # Core financial scores based on ratios
            details = _build_metric_scores(info)

            # Detailed raw fundamental metrics
            raw_metrics = {
                "total_revenue": _safe_float(info.get("totalRevenue")),
                "revenue_growth": _safe_float(info.get("revenueGrowth")),
                "gross_margins": _safe_float(info.get("grossMargins")),
                "operating_margins": _safe_float(info.get("operatingMargins")),
                "trailing_pe": _safe_float(info.get("trailingPE")),
                "forward_pe": _safe_float(info.get("forwardPE")),
                "price_to_sales": _safe_float(info.get("priceToSalesTrailing12Months")),
                "debt_to_equity": _safe_float(info.get("debtToEquity")),
                "free_cashflow": _safe_float(info.get("freeCashflow")),
                "return_on_equity": _safe_float(info.get("returnOnEquity"))
            }

            combined_details = {
                "company_name": company_name,
                "symbol": resolved_symbol,
                "status": "listed",
                "market": market_name,
                "market_cap": market_cap,
                "market_cap_category": classify_market_cap(market_cap),
                "currency": info.get("currency", "USD"),
                "raw_metrics": raw_metrics,
                "availability": "available",
                "data_source": "yfinance",
                "financial_score": {
                    "overall_score": details["overall_score"],
                    "score_coverage": details["score_coverage"],
                    "score_detail": (
                        "Weighted score using revenue growth, gross margin, "
                        "operating margin, EBITDA margin, and free cash flow margin."
                    ),
                },
                "metric_scores": details["metric_scores"],
            }

            combined_details["ai_summary"] = _build_summary(
                company_name,
                "listed",
                details,
                market_name,
            )

            return combined_details

        except Exception as exc:
            logger.error("Public financial lookup failed for %s: %s", query, exc)

    # ---------------------------------------------------------
    # 2. SEC reference & Private-company fallback
    # ---------------------------------------------------------
    sec_reference = _lookup_sec_company(query)

    # If the company is private and evidence was provided
    if private_evidence:
        scoring = score_private_company_metrics(private_evidence)

        result = {
            "company_name": query,
            "symbol": None,
            "status": "private",
            "market": "Public market",
            "market_cap": None,
            "market_cap_category": "Unknown",
            "raw_metrics": {},  # Keep consistent structure
            "availability": "partial",
            "data_source": "web_evidence",
            "financial_score": {
                "overall_score": scoring["overall_score"],
                "score_coverage": scoring["score_coverage"],
                "average_evidence_confidence": scoring["average_evidence_confidence"],
            },
            "metric_scores": scoring["metric_scores"],
            "financial_evidence": private_evidence,
            "search_queries": build_private_company_search_queries(query),
            "sec_reference": sec_reference,
        }

        result["ai_summary"] = _build_summary(
            query,
            "private",
            result["financial_score"],
        )

        return result

    # ---------------------------------------------------------
    # 3. Nothing found / Web research required
    # ---------------------------------------------------------
    return {
        "company_name": query,
        "symbol": None,
        "status": "private_or_unverified" if sec_reference else "private",
        "market": "Public market",
        "market_cap": None,
        "market_cap_category": "Unknown",
        "raw_metrics": {},
        "availability": "unavailable",
        "data_source": "SEC" if sec_reference else "web_research_required",
        "financial_score": {
            "overall_score": 0,
            "score_coverage": 0,
        },
        "metric_scores": {},
        "financial_evidence": [],
        "search_queries": build_private_company_search_queries(query),
        "sec_reference": sec_reference,
        "ai_summary": (
            f"No sufficiently reliable financial information was found for {query}. "
            "The company may be private, or available financial information could not be verified. "
            "No financial figures were fabricated."
        ),
    }


if __name__ == "__main__":
    import json
    import sys

    # Enable logging output to see warnings/debug logs
    logging.basicConfig(level=logging.INFO)

    # Grab the search query from terminal argument, or default to "AAPL"
    query = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

    print(f"\n--- Testing public company lookup for: {query} ---")
    res = get_company_financials(query)
    print(json.dumps(res, indent=2))

    # Optional: Test private company workflow if a second argument '--private' is passed
    if "--private" in sys.argv:
        print("\n--- Testing private company workflow with dummy evidence ---")
        dummy_evidence = [
            make_financial_evidence(
                metric_name="revenue_growth",
                value=0.25,
                source_type="reputable_news",
                confidence="medium",
                notes="CEO interview on Bloomberg",
            ),
            make_financial_evidence(
                metric_name="gross_margin",
                value=0.55,
                source_type="company_reported",
                confidence="high",
            ),
        ]
        private_res = get_company_financials("Stripe", private_evidence=dummy_evidence)
        print(json.dumps(private_res, indent=2))