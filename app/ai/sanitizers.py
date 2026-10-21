import re

JAILBREAK_PATTERNS = [
     r"you are (now )?(a )?(developer|admin|unrestricted)",
    r"ignore (all )?(previous|above) instructions",
    r"system prompt",
    r"act as",
    r"dan mode",
    r"reveal (your )?secret",
    r"sudo mode"
]

def sanitize_user_prompt(prompt : str) -> tuple[bool, str]:
    prompt_lower = prompt.lower().strip()
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, prompt_lower):
            return False, "Jailbreak detected"
    return True, "Prompt is safe" 