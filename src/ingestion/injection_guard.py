import re
from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel, Field


class InjectionScanResult(BaseModel):
    """
    Result of deterministic prompt-injection scan.
    Fulfills CONTEXT_UPDATED.md Section 15.2.
    """
    is_injection_attempt: bool = Field(default=False)
    injection_status: str = Field(
        default="none_detected",
        description="'none_detected', 'flagged', 'uncertain', 'quarantined'"
    )
    matched_spans: List[str] = Field(default_factory=list, description="Text spans matching injection rules")
    rule_ids: List[str] = Field(default_factory=list, description="IDs of rules triggered")
    retrieval_policy: str = Field(
        default="allow",
        description="'allow', 'exclude', or 'quarantined'. Flagged items are excluded by default."
    )
    content_untrusted: bool = Field(
        default=True,
        description="All document text is permanently labeled untrusted data, never instructions."
    )


class InjectionGuard:
    """
    Deterministic prompt-injection scanner.
    Operates via compiled regular expressions before chunking/embedding.
    """

    SCANNER_VERSION = "1.0.0"

    RULES: Dict[str, Tuple[str, re.Pattern]] = {
        "RULE-01-INSTRUCTION-OVERRIDE": (
            "Direct instruction override",
            re.compile(
                r"(?i)\b(ignore|disregard|forget|bypass)\s+(all\s+)?(previous\s+|prior\s+|system\s+)?(instructions|rules|prompts|directives|guidelines)\b"
            ),
        ),
        "RULE-02-PERSONA-HIJACK": (
            "Role or persona impersonation attempt",
            re.compile(
                r"(?i)\b(you\s+are\s+now|pretend\s+you\s+are|roleplay\s+as|act\s+as\s+a|your\s+new\s+role\s+is)\b"
            ),
        ),
        "RULE-03-SYSTEM-IMPERSONATION": (
            "System / developer message tag impersonation",
            re.compile(
                r"(?i)(<\|?(system|developer|assistant|im_start|im_end)\|?>|\[(system|developer)\]|system\s*:\s*|developer\s+message\s*:)"
            ),
        ),
        "RULE-04-TOOL-MANIPULATION": (
            "Tool execution injection",
            re.compile(
                r"(?i)\b(call\s+tool|execute\s+command|run\s+tool|invoke_tool|call_function)\s*[:\(]"
            ),
        ),
        "RULE-05-OUTCOME-MANDATE": (
            "Adversarial outcome forcing (zero exposure or panic forcing)",
            re.compile(
                r"(?i)\b(declare|conclude|rule\s+that|state\s+that)\s+(exposure\s+is\s+(zero|0%|none)|there\s+is\s+zero\s+risk|the\s+trial\s+must\s+close)\b"
            ),
        ),
        "RULE-06-SECRET-PROMPT-EXTRACTION": (
            "Prompt or secret leakage request",
            re.compile(
                r"(?i)\b(reveal|print|output|display|show)\s+(your\s+)?(system\s+prompt|instructions|internal\s+memory|secret\s+key|private\s+memory)\b"
            ),
        ),
    }

    def scan(self, text: str) -> InjectionScanResult:
        """
        Scans document text against all compiled regex rules.
        """
        if not text or not text.strip():
            return InjectionScanResult()

        matched_spans: List[str] = []
        triggered_rules: List[str] = []

        for rule_id, (description, pattern) in self.RULES.items():
            matches = pattern.finditer(text)
            for m in matches:
                # Capture matched span (truncated if excessively long)
                span_text = m.group(0)[:100]
                matched_spans.append(span_text)
                if rule_id not in triggered_rules:
                    triggered_rules.append(rule_id)

        if triggered_rules:
            return InjectionScanResult(
                is_injection_attempt=True,
                injection_status="flagged",
                matched_spans=matched_spans,
                rule_ids=triggered_rules,
                retrieval_policy="exclude",  # Exclude from evidence by default per Sec 15.2
                content_untrusted=True,
            )

        return InjectionScanResult(
            is_injection_attempt=False,
            injection_status="none_detected",
            matched_spans=[],
            rule_ids=[],
            retrieval_policy="allow",
            content_untrusted=True,
        )


_injection_guard: Optional[InjectionGuard] = None

def get_injection_guard() -> InjectionGuard:
    global _injection_guard
    if _injection_guard is None:
        _injection_guard = InjectionGuard()
    return _injection_guard
