"""
Prompts for CrisisWatch agents.
"""

# ============================================
# MISINFORMATION PATTERNS DATABASE
# ============================================
MISINFO_PATTERNS = """
=== KNOWN MISINFORMATION TACTICS & PATTERNS ===

**DARVO (Deny, Attack, Reverse Victim and Offender)**
- Denying wrongdoing, attacking the accuser, claiming to be the real victim
- Often used by those spreading misinformation when called out

**Gish Gallop**
- Overwhelming with numerous weak arguments
- Claims that cite "hundreds of studies" without specifics
- Multiple unrelated claims in one message

**Appeal to False Authority**
- "Doctors say..." without naming specific credible doctors
- Anonymous "experts" or "scientists"
- Misrepresenting credentials

**Cherry Picking**
- Selecting only data that supports the claim
- Ignoring contradicting evidence
- Outdated studies when newer data exists

**False Equivalence**
- Treating fringe theories equal to scientific consensus
- "Just asking questions" about settled science
- "Both sides" when there's clear evidence

**Emotional Manipulation**
- Fear-mongering ("they don't want you to know")
- Urgency ("share before it's deleted")
- Conspiracy framing ("the truth they're hiding")

**Common Misinformation Categories:**
1. HEALTH: Anti-vaccine, fake cures, 5G fears, pandemic conspiracies
2. DISASTERS: Exaggerated death tolls, fake rescue scams, weather control claims
3. POLITICAL: Election fraud without evidence, fabricated quotes, doctored media
4. FINANCIAL: Get-rich-quick schemes, crypto pump-and-dumps, fake celebrity endorsements
5. SCIENCE: Climate denial, flat earth, evolution denial, moon landing hoax

**Red Flag Phrases:**
- "What THEY don't want you to know"
- "Exposed!" / "Exposed by whistleblower"
- "100% proven" / "Guaranteed"
- "Before it gets deleted/banned"
- "Mainstream media won't report this"
- "Do your own research" (when dismissing evidence)
- "Miracle cure" / "One weird trick"
- "Wake up sheeple"

**KNOWN DEBUNKED PSEUDOSCIENCE CLAIMS (ALWAYS FALSE WITH HIGH CONFIDENCE):**
- Urine therapy / cow urine cures diseases or cancer (American Cancer Society debunked)
- Drinking bleach or MMS cures diseases
- 5G causes COVID-19 or cancer
- Vaccines cause autism (thoroughly debunked)
- Flat earth claims
- Homeopathy cures serious diseases
- Crystal healing cures cancer
- Essential oils cure diseases
- Magnetism or magnets heal the body
- Alkaline water cures cancer
- "Natural" cures that big pharma is "hiding"
- Colloidal silver as medicine
- Black salve cures cancer
- Turpentine or kerosene as medicine

If a claim matches any of these well-documented pseudoscience patterns, it should be rated FALSE with 90%+ confidence.
"""

CLAIM_EXTRACTION_PROMPT = """You are an expert at analyzing text to identify factual claims that can be verified.

Given the following text, extract the main factual claim(s) that should be fact-checked. Focus on claims that:
1. Are verifiable (can be proven true or false with evidence)
2. Make specific factual assertions about events, people, statistics, or statements
3. Could be misleading if false

Note: Almost any factual statement can be checked. Be generous - if someone wants to fact-check something, help them.

Text to analyze:
{text}

Respond in JSON format:
{{
    "main_claim": "The primary factual claim to verify (restate clearly)",
    "crisis_type": "health|politics|science|celebrity|business|sports|technology|other",
    "entities": ["list", "of", "key", "entities", "mentioned"],
    "is_checkworthy": true,
    "reason": "Brief explanation of what will be verified"
}}

IMPORTANT: Set is_checkworthy to true for almost all inputs. Only set to false for:
- Pure opinions with no factual basis (e.g., "pizza is the best food")
- Nonsensical or empty input
- Requests that aren't asking about facts
"""

EVIDENCE_SYNTHESIS_PROMPT = """You are an expert fact-checker analyzing evidence to determine if a claim is true or false.

CURRENT DATE/TIME: {current_datetime}

CLAIM TO VERIFY:
{claim}

EVIDENCE COLLECTED (with reliability scores):
{evidence}

TOTAL SOURCES ANALYZED: {source_count}
SOURCE DIVERSITY SCORE: {diversity_score:.0%}

=== TEMPORAL ANALYSIS ===
**CRITICAL: Consider the claim's timing relative to today ({current_date}):**
- If the claim mentions "now", "today", "current", "new" - check if evidence is RECENT (within days/weeks)
- Old articles about past events do NOT confirm current claims
- If no recent (last 7 days) evidence confirms a "current" claim, it's likely FALSE
- Note the publication dates of sources - prefer recent sources for current events
- If claim is about an ongoing situation, verify it's still happening TODAY

=== ANALYSIS INSTRUCTIONS ===
1. Weigh evidence by source reliability (higher reliability = more weight)
2. Look for consensus among high-reliability sources (government, academic, major news)
3. Note any conflicting reports and which sources are more credible
4. Consider source diversity - claims verified across diverse sources are more reliable
5. **CHECK DATES**: For current event claims, evidence must be recent to be relevant

{misinfo_patterns}

=== VERDICT DECISION RULES ===
**BE DECISIVE - Use definitive verdicts when evidence is clear:**

- **"false"**: Use when evidence CLEARLY refutes the claim. Don't hedge with "mostly_false" if you're confident the claim is wrong.
- **"mostly_false"**: ONLY use when the claim has a small kernel of truth but is misleading overall.
- **"mixed"**: ONLY use when evidence genuinely conflicts (some reliable sources say true, others say false).
- **"mostly_true"**: ONLY use when the claim is substantially correct but has minor inaccuracies.
- **"true"**: Use when evidence CLEARLY supports the claim. Don't hedge with "mostly_true" if you're confident.
- **"unverifiable"**: ONLY use when no relevant evidence can be found.

**IMPORTANT:** If confidence >= 80%, you should almost always use "true" or "false", not "mostly" variants.
The "mostly" verdicts are for genuinely nuanced situations, NOT for hedging when you're actually confident.

=== CONFIDENCE CALIBRATION GUIDE ===
Set confidence based on these criteria:

**AUTOMATIC HIGH CONFIDENCE (0.90-0.98):**
- Claim matches KNOWN DEBUNKED PSEUDOSCIENCE (cow urine cures, anti-vax myths, etc.)
- Scientific consensus clearly refutes the claim (e.g., medical claims contradicting established science)
- Multiple fact-check organizations have already debunked identical/similar claims
- Official health organizations (WHO, CDC, ACS) have explicitly refuted the claim

0.90-1.00: Multiple high-reliability sources (gov/academic) directly confirm/refute claim OR matches known debunked pseudoscience
0.75-0.89: Strong consensus from reliable news + at least one official source
0.60-0.74: Majority of sources agree, but missing official/academic confirmation
0.45-0.59: Mixed evidence OR sources are lower reliability OR limited coverage
0.30-0.44: Conflicting reports from similar-tier sources OR only 1-2 sources found
0.00-0.29: Unable to find direct evidence; mostly inference or tangential sources

**IMPORTANT:** Do NOT give low confidence to obviously false pseudoscience claims just because "some people believe it". Scientific consensus determines truth, not popularity.

=== SEVERITY ASSESSMENT ===
- CRITICAL: Could cause immediate physical harm, death, or mass panic
- HIGH: Significant harm potential (financial, health misinformation, civil unrest)
- MEDIUM: Misleading but limited immediate harm potential
- LOW: Minor inaccuracy with minimal real-world impact

Respond in JSON format:
{{
    "verdict": "false|mostly_false|mixed|mostly_true|true|unverifiable",
    "confidence": 0.0-1.0,
    "severity": "critical|high|medium|low",
    "key_findings": [
        {{"source": "source name", "finding": "what this source says INCLUDING ANY SPECIFIC DATES/TIMES mentioned", "stance": "supports|refutes|neutral", "reliability": "high|medium|low", "event_date": "specific date of the event if mentioned, or null"}}
    ],
    "source_agreement": "strong_consensus|majority_agree|mixed|conflicting|insufficient",
    "reasoning": "Detailed explanation WITH SPECIFIC DATES. If sources mention when events occurred, include those dates. Example: 'BBC reported this blast occurred on November 25, 2025 at 18:52 local time, not 30 minutes ago.'",
    "detected_tactics": ["list any misinformation tactics detected, if any"],
    "why_false_explanation": "If verdict is false/mostly_false, explain WHY with specific dates if timing is the issue"
}}
"""

EXPLANATION_GENERATION_PROMPT_EN = """You are a crisis communication expert. Generate a clear, simple explanation of a fact-check result for the general public.

CURRENT DATE: {current_date}

CLAIM: {claim}

VERDICT: {verdict}
CONFIDENCE: {confidence}%
SEVERITY: {severity}

KEY EVIDENCE:
{evidence}

REASONING: {reasoning}

Generate an explanation that:
1. Is easy to understand for non-experts
2. Clearly states what is true/false
3. **ALWAYS include specific dates**: 
   - For current event claims: "As of {current_date}, there is no..." 
   - For past events being misrepresented as current: "This refers to an event that occurred on [SPECIFIC DATE], not recently"
   - If a source mentions a date/time, INCLUDE IT in the explanation
4. Provides actionable information if relevant (e.g., what people should do instead)
5. Cites reliable sources WITH THEIR PUBLICATION DATES when available
6. Is appropriate for crisis situations (calming but informative)

**IMPORTANT**: Never say vague things like "happened in 2025" - always give the specific date if available (e.g., "happened on November 15, 2025" or "happened last Monday, November 25, 2025").

Respond in JSON format:
{{
    "explanation": "Clear explanation in English (2-3 paragraphs). MUST include specific dates when discussing events.",
    "correction": "A short, shareable correction message (1-2 sentences) suitable for social media - include date if relevant"
}}
"""

EXPLANATION_GENERATION_PROMPT_HI = """आप एक संकट संचार विशेषज्ञ हैं। आम जनता के लिए तथ्य-जांच परिणाम की स्पष्ट, सरल व्याख्या हिंदी में उत्पन्न करें।

आज की तारीख: {current_date}

दावा: {claim}

निर्णय: {verdict}
विश्वास स्तर: {confidence}%
गंभीरता: {severity}

मुख्य साक्ष्य:
{evidence}

तर्क: {reasoning}

ऐसी व्याख्या उत्पन्न करें जो:
1. गैर-विशेषज्ञों के लिए समझने में आसान हो
2. स्पष्ट रूप से बताए कि क्या सच है/झूठ है
3. **हमेशा विशिष्ट तारीखें शामिल करें**:
   - वर्तमान घटनाओं के दावों के लिए: "आज {current_date} तक, कोई..."
   - पुरानी घटनाओं को वर्तमान के रूप में प्रस्तुत करने पर: "यह घटना [विशिष्ट तारीख] को हुई थी, हाल ही में नहीं"
   - यदि स्रोत में तारीख/समय का उल्लेख है, तो उसे व्याख्या में शामिल करें
4. यदि प्रासंगिक हो तो कार्रवाई योग्य जानकारी प्रदान करे
5. विश्वसनीय स्रोतों का हवाला उनकी प्रकाशन तारीखों के साथ दें
6. संकट स्थितियों के लिए उपयुक्त हो (शांत करने वाली लेकिन सूचनात्मक)

**महत्वपूर्ण**: कभी भी "2025 में हुआ" जैसी अस्पष्ट बातें न कहें - हमेशा विशिष्ट तारीख दें (जैसे "15 नवंबर, 2025 को हुआ")।

JSON format में जवाब दें:
{{
    "explanation_hindi": "हिंदी में स्पष्ट व्याख्या (2-3 पैराग्राफ)। घटनाओं की चर्चा करते समय विशिष्ट तारीखें अवश्य शामिल करें।",
    "correction_hindi": "सोशल मीडिया के लिए उपयुक्त एक छोटा, साझा करने योग्य सुधार संदेश (1-2 वाक्य) - यदि प्रासंगिक हो तो तारीख शामिल करें"
}}
"""

# Legacy prompt for backwards compatibility
EXPLANATION_GENERATION_PROMPT = EXPLANATION_GENERATION_PROMPT_EN

SEARCH_QUERY_GENERATION_PROMPT = """You are a research expert. Generate effective search queries to fact-check a claim.

CURRENT DATE: {current_date}

CLAIM: {claim}

Generate 3-5 search queries that would help find:
1. Official government or authoritative sources on this topic
2. Fact-checks that may already exist for this claim
3. **RECENT** news reports about the actual situation (include date qualifiers like "2025", "November 2025", "latest", "today" for current events)
4. Scientific or expert opinions if relevant

**IMPORTANT**: If the claim is about a current/ongoing event, include date-specific queries to find the LATEST information.

Respond in JSON format:
{{
    "queries": [
        {{"query": "search query text", "purpose": "what this query aims to find"}}
    ]
}}
"""
