"""
Prompts for CrisisWatch agents.
"""

CLAIM_EXTRACTION_PROMPT = """You are an expert at analyzing text to identify factual claims that can be verified.

Given the following text, extract the main factual claim(s) that should be fact-checked. Focus on claims that:
1. Are verifiable (can be proven true or false with evidence)
2. Relate to crisis situations (natural disasters, health emergencies, civil unrest, etc.)
3. Could cause harm if false (dangerous advice, misinformation, panic-inducing)

Text to analyze:
{text}

Respond in JSON format:
{{
    "main_claim": "The primary factual claim to verify",
    "crisis_type": "earthquake|flood|health|civil_unrest|other|none",
    "entities": ["list", "of", "key", "entities", "mentioned"],
    "is_checkworthy": true/false,
    "reason": "Brief explanation of why this claim should/shouldn't be checked"
}}
"""

EVIDENCE_SYNTHESIS_PROMPT = """You are an expert fact-checker analyzing evidence to determine if a claim is true or false.

CLAIM TO VERIFY:
{claim}

EVIDENCE COLLECTED (with reliability scores):
{evidence}

TOTAL SOURCES ANALYZED: {source_count}
SOURCE DIVERSITY SCORE: {diversity_score:.0%}

=== ANALYSIS INSTRUCTIONS ===
1. Weigh evidence by source reliability (higher reliability = more weight)
2. Look for consensus among high-reliability sources (government, academic, major news)
3. Note any conflicting reports and which sources are more credible
4. Consider source diversity - claims verified across diverse sources are more reliable

=== KNOWN MISINFORMATION PATTERNS ===
Be ASSERTIVE when claims match well-documented misinformation:
- Medical: Anti-vaccine claims, fake cures (bleach, ivermectin for COVID), 5G health fears
- Disasters: Exaggerated death tolls, fake rescue scams, false government conspiracy claims
- If a claim contradicts scientific consensus from WHO, CDC, or peer-reviewed research, rate as FALSE with HIGH confidence (0.85+)

=== CONFIDENCE CALIBRATION GUIDE ===
Set confidence based on these criteria:

0.90-1.00: Multiple high-reliability sources (gov/academic) directly confirm/refute claim
0.75-0.89: Strong consensus from reliable news + at least one official source
0.60-0.74: Majority of sources agree, but missing official/academic confirmation
0.45-0.59: Mixed evidence OR sources are lower reliability OR limited coverage
0.30-0.44: Conflicting reports from similar-tier sources OR only 1-2 sources found
0.00-0.29: Unable to find direct evidence; mostly inference or tangential sources

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
        {{"source": "source name", "finding": "what this source says", "stance": "supports|refutes|neutral", "reliability": "high|medium|low"}}
    ],
    "source_agreement": "strong_consensus|majority_agree|mixed|conflicting|insufficient",
    "reasoning": "Detailed explanation of how you reached this verdict, referencing specific sources and their reliability"
}}
"""

EXPLANATION_GENERATION_PROMPT_EN = """You are a crisis communication expert. Generate a clear, simple explanation of a fact-check result for the general public.

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
3. Provides actionable information if relevant (e.g., what people should do instead)
4. Cites reliable sources
5. Is appropriate for crisis situations (calming but informative)

Respond in JSON format:
{{
    "explanation": "Clear explanation in English (2-3 paragraphs)",
    "correction": "A short, shareable correction message (1-2 sentences) suitable for social media"
}}
"""

EXPLANATION_GENERATION_PROMPT_HI = """आप एक संकट संचार विशेषज्ञ हैं। आम जनता के लिए तथ्य-जांच परिणाम की स्पष्ट, सरल व्याख्या हिंदी में उत्पन्न करें।

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
3. यदि प्रासंगिक हो तो कार्रवाई योग्य जानकारी प्रदान करे
4. विश्वसनीय स्रोतों का हवाला दे
5. संकट स्थितियों के लिए उपयुक्त हो (शांत करने वाली लेकिन सूचनात्मक)

JSON format में जवाब दें:
{{
    "explanation_hindi": "हिंदी में स्पष्ट व्याख्या (2-3 पैराग्राफ)",
    "correction_hindi": "सोशल मीडिया के लिए उपयुक्त एक छोटा, साझा करने योग्य सुधार संदेश (1-2 वाक्य)"
}}
"""

# Legacy prompt for backwards compatibility
EXPLANATION_GENERATION_PROMPT = EXPLANATION_GENERATION_PROMPT_EN

SEARCH_QUERY_GENERATION_PROMPT = """You are a research expert. Generate effective search queries to fact-check a claim.

CLAIM: {claim}

Generate 3-5 search queries that would help find:
1. Official government or authoritative sources on this topic
2. Fact-checks that may already exist for this claim
3. News reports about the actual situation
4. Scientific or expert opinions if relevant

Respond in JSON format:
{{
    "queries": [
        {{"query": "search query text", "purpose": "what this query aims to find"}}
    ]
}}
"""
