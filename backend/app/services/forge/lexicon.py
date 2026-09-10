"""Shared English lexical utilities for the deterministic validators.

One home for the stop-word list, the light stemmer and the "content term"
extractor that the compiler, validators, firewall and continuity guard all
need. Keeping them here prevents three slightly different copies of the same
heuristic from drifting apart (they did: ``_PROHIBITED_STOP``, ``_COMMON_CAP``
and ``_EN_STOP`` each knew about a different subset of English).

Everything is pure, deterministic and cheap. Korean text is handled by the
callers (whitespace eojeol tokens; no stemming).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, List, Sequence, Set

# ---------------------------------------------------------------- stop words
# Function words plus the small closed classes (pronouns, determiners, modals,
# common adverbs) that carry no propositional content. A plot spoiler can never
# hinge on one of these.
STOP_WORDS: Set[str] = {
    # articles / determiners / quantifiers
    "a", "an", "the", "this", "that", "these", "those", "some", "any", "all", "each", "every", "both", "either", "neither", "no", "none", "few", "many", "most", "much", "several", "such", "own", "same", "other", "another", "whole", "half", "enough", "little", "less", "more", "very", "too", "quite", "rather",
    # pronouns
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "we", "us", "our", "ours", "ourselves", "they", "them", "their", "theirs", "themselves", "who", "whom", "whose", "which", "what", "whatever", "whoever", "someone", "somebody", "something", "anyone", "anybody", "anything", "everyone", "everybody", "everything", "nobody", "nothing", "one", "ones",
    # prepositions / conjunctions
    "of", "to", "in", "on", "at", "by", "for", "with", "from", "into", "onto", "upon", "over", "under", "above", "below", "between", "among", "through", "across", "along", "around", "about", "against", "before", "after", "during", "until", "till", "since", "within", "without", "toward", "towards", "behind", "beside", "beyond", "near", "off", "out", "up", "down", "and", "or", "nor", "but", "so", "yet", "if", "then", "than", "because", "as", "while", "whereas", "although", "though", "unless", "whether", "once", "when", "whenever", "where", "wherever", "why", "how",
    # auxiliaries / modals / copulas
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "ought", "need", "dare",
    "not", "don", "doesn", "didn", "won", "wouldn", "shouldn", "couldn", "cannot", "isn", "aren", "wasn", "weren", "hasn", "haven", "hadn", "ll", "ve", "re", "d", "s", "t", "m",
    # common adverbs / discourse
    "here", "there", "now", "again", "also", "just", "only", "even", "still", "already", "always", "never", "often", "sometimes", "soon", "later", "ever", "almost", "really", "actually", "perhaps", "maybe", "instead", "well", "yes", "okay", "please", "back", "away", "far", "long", "else", "however", "therefore", "meanwhile", "somehow", "somewhere", "nowhere", "anywhere", "everywhere",
    # high-frequency verbs of narration (say/go/come/look/... in all inflections are added below)
    "say", "said", "says", "saying", "tell", "told", "tells", "telling", "ask", "asked", "asks", "asking", "go", "went", "goes", "going", "gone", "come", "came", "comes", "coming", "get", "got", "gets", "getting", "gotten", "make", "made", "makes", "making", "take", "took", "takes", "taking", "taken", "give", "gave", "gives", "giving", "given", "see", "saw", "sees", "seeing", "seen", "look", "looked", "looks", "looking", "know", "knew", "knows", "knowing", "known", "think", "thought", "thinks", "thinking", "feel", "felt", "feels", "feeling", "want", "wanted", "wants", "wanting", "let", "lets", "letting", "keep", "kept", "keeps", "keeping", "seem", "seemed", "seems", "seeming", "turn", "turned", "turns", "turning", "put", "puts", "putting", "leave", "left", "leaves", "leaving", "stand", "stood", "stands", "standing", "sit", "sat", "sits", "sitting", "walk", "walked", "walks", "walking", "begin", "began", "begins", "beginning", "begun", "try", "tried", "tries", "trying", "use", "used", "uses", "using", "find", "found", "finds", "finding", "hear", "heard", "hears", "hearing", "call", "called", "calls", "calling", "become", "became", "becomes", "becoming", "happen", "happened", "happens", "happening", "mean", "meant", "means", "meaning", "way", "ways", "thing", "things", "time", "times", "day", "days", "night", "nights", "moment", "moments", "man", "men", "woman", "women", "people", "person", "hand", "hands", "eye", "eyes", "face", "head", "voice", "door", "room", "place", "part", "kind", "sort",
    # planning / meta vocabulary that appears in outline text but never in prose as content
    "chapter", "chapters", "planned", "plan", "outline", "beat", "beats", "scene", "scenes", "reveal", "reveals", "revealed", "revealing", "payoff", "window", "pov", "unaware", "reader", "readers", "finally", "eventually", "ultimately", "learns", "learn", "learned", "discovers", "discover", "discovered", "realizes", "realize", "realized", "realises", "realise", "realised", "starts", "start", "started", "ends", "end", "ended", "shows", "show", "shown", "showed", "hint", "hints", "regarding", "concerning", "true", "truth", "truly", "secret", "secrets", "secretly", "identity", "fact", "facts",
}

# Words that are capitalised in prose for reasons other than being a name:
# sentence-initial function words, titles, numbers, colours, time words.
_NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "hundreds", "thousand", "thousands", "million", "millions", "billion",
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth", "twentieth", "last", "next", "once", "twice", "thrice", "dozen", "dozens", "half", "quarter",
}
_TITLES = {"mr", "mrs", "ms", "miss", "sir", "madam", "madame", "lord", "lady", "master", "mistress", "captain", "commander", "general", "colonel", "major", "sergeant", "lieutenant", "doctor", "dr", "professor", "father", "mother", "brother", "sister", "uncle", "aunt", "king", "queen", "prince", "princess", "duke", "duchess", "count", "countess", "baron", "baroness", "earl", "marquis", "emperor", "empress", "saint", "pope", "bishop", "priest", "priestess", "god", "goddess", "hero", "heroine", "villain", "demon", "elder", "chief", "boss", "teacher", "student", "students", "senior", "junior", "young", "old", "guild", "clan", "house", "order", "empire", "kingdom", "academy", "system", "status", "level", "skill", "quest"}
_COLOURS_TIME = {"black", "white", "red", "blue", "green", "yellow", "gold", "golden", "silver", "grey", "gray", "brown", "crimson", "scarlet", "violet", "purple", "pink", "orange", "amber", "ivory", "morning", "evening", "afternoon", "noon", "midnight", "dawn", "dusk", "today", "tomorrow", "yesterday", "tonight", "spring", "summer", "autumn", "fall", "winter", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "june", "july", "august", "september", "october", "november", "december", "north", "south", "east", "west", "heaven", "hell", "earth", "sun", "moon", "star", "stars", "sky", "sea", "death", "life", "fate", "fortune", "silence", "nothing", "everything"}
_INTERJECTIONS = {"oh", "ah", "aha", "ha", "hmm", "hm", "huh", "uh", "um", "er", "wow", "ouch", "alas", "hey", "hello", "hi", "goodbye", "bye", "thanks", "thank", "sorry", "fine", "good", "great", "right", "wrong", "true", "false", "sure", "indeed", "exactly", "wait", "stop", "look", "listen", "run", "hurry", "quick", "quiet", "enough", "no", "yes", "never", "nothing", "damn", "hell", "god"}

# Sentence-initial capitalised words that are not names: everything above plus
# the stop-word list. The set is lowercase; compare with ``word.lower()``.
NON_NAME_WORDS: Set[str] = STOP_WORDS | _NUMBER_WORDS | _TITLES | _COLOURS_TIME | _INTERJECTIONS

_WORD_RX = re.compile(r"[a-z][a-z'\-]*[a-z]|[a-z]")
_LATIN_RX = re.compile(r"[A-Za-z\u00c0-\u024f']+")

# Inflectional suffixes only (number, tense, aspect). Derivational suffixes
# (-er, -ly, -ment, -ness) are deliberately *not* stripped: "courier" is not
# "couri", "supply" is not "supp". It is better to miss "stabilization" ~
# "stabilize" than to conflate unrelated words.
_SUFFIXES: Sequence[str] = ("ings", "ing", "ied", "ies", "ed", "es", "s")
_KEEP_S = ("ss", "us", "is")  # glass, virus, crisis


@lru_cache(maxsize=65536)
def stem(word: str) -> str:
    """Conservative light stemmer for inflection-tolerant matching.

    ``reveals/revealed/revealing -> reveal``, ``forges/forging/forged -> forg``,
    ``manifests -> manifest``, ``supplies -> suppli``, ``stabbed -> stab``,
    ``running -> run``; ``courier``, ``supply``, ``golden`` are unchanged.

    Never shortens a word below three letters and keeps a trailing ``s`` that is
    part of the root (``glass``). Doubled final consonants left by ``-ed``/``-ing``
    are collapsed.
    """
    w = word.lower().strip("'\"“”‘’")
    if len(w) <= 3:
        return w
    for suf in _SUFFIXES:
        if not w.endswith(suf) or len(w) - len(suf) < 3:
            continue
        if suf == "s" and w.endswith(_KEEP_S):
            return w
        base = w[: -len(suf)]
        if suf in ("ies", "ied"):
            return base + "i"
        if suf == "es":
            # boxes/wishes/forges -> box/wish/forg ; notes -> note (keep the e for short bases)
            return base if (base.endswith(("sh", "ch", "x", "z", "ss")) or len(base) >= 4) else w[:-1]
        if suf in ("ed", "ing", "ings") and len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "aeiouy":
            base = base[:-1]
        return base
    return w


def tokenize_words(text: str) -> List[str]:
    """Lowercased Latin word tokens; apostrophes are kept inside words (``don't``) so callers can drop clitics."""
    return [w.lower() for w in _LATIN_RX.findall(text or "")]


def content_terms(text: str, *, min_len: int = 3, extra_stop: Iterable[str] = ()) -> List[str]:
    """Distinct content words of ``text`` in order of appearance.

    Strips stop words, clitic fragments (``'ve``, ``'t``), numbers spelled out and
    anything shorter than ``min_len``. Does *not* stem: callers compare with
    :func:`stem` when they want inflection tolerance.
    """
    stop = STOP_WORDS | _NUMBER_WORDS | {s.lower() for s in extra_stop}
    out: List[str] = []
    seen: Set[str] = set()
    for tok in tokenize_words(text):
        # "don't" -> "don" + "t": drop the clitic and the stop word both.
        head = tok.split("'")[0] if "'" in tok else tok
        head = head.strip("-")
        if len(head) < min_len or head in stop:
            continue
        if head not in seen:
            seen.add(head)
            out.append(head)
    return out


# Endings that English proper names essentially never carry. ``-ed``/``-ing``/``-ly``
# are *not* here: Reed, Sterling, Harding, Italy, Emily and Tessaly are names. Those
# are handled by stripping the suffix and checking whether an ordinary word remains
# ("Opened" -> open, "Counting" -> count, "Suddenly" -> sudden).
_VERBISH_RX = re.compile(r"(?:tion|sion|ness|ment)$")
_ADVERB_RX = re.compile(r"^(?P<stem>[a-z]{3,})(?:ly|ily|ally)$")


def is_non_name_word(word: str) -> bool:
    """True when a capitalised ``word`` is an ordinary English word rather than a proper name.

    Covers the closed classes (stop words, numbers, titles, colours, time words,
    interjections), inflected forms of common words (``Kept``, ``Counting``,
    ``Opened``, ``Adjusted``) and adverbs whose stem is an ordinary word
    (``Suddenly``, ``Carefully``); ``Sterling``, ``Reed``, ``Tessaly`` remain names.
    """
    w = word.lower().strip("'\"“”‘’")
    if not w:
        return True
    if w in NON_NAME_WORDS:
        return True
    st = stem(w)
    if st != w and (st in NON_NAME_WORDS or st in _COMMON_STEMS):
        # An inflected form of an ordinary verb ("Opened", "Counting", "Kept"). Adjectives
        # and colours only inflect as adjectives, so "Harding"/"Redding" stay names.
        return st not in _ADJECTIVE_STEMS
    if len(w) > 5 and _VERBISH_RX.search(w):
        return True
    m = _ADVERB_RX.match(w)
    if m:
        s = m.group("stem")
        return s in NON_NAME_WORDS or s in _COMMON_STEMS or s in _ADJECTIVE_STEMS or stem(s) in NON_NAME_WORDS
    return False


# Stems of common verbs that appear capitalised at sentence starts in inflected form
# ("Opened", "Adjusted", "Counting") and are not otherwise in the closed-class lists.
_COMMON_STEMS = {
    "open", "close", "shut", "count", "adjust", "watch", "wait", "stop", "start", "move", "stay", "hold", "drop", "pull", "push", "lift", "carry", "bring", "send", "show", "follow", "reach", "touch", "pass", "cross", "climb", "fall", "rise", "run", "step", "jump", "stand", "sit", "lie", "lay", "sleep", "wake", "breathe", "listen", "speak", "talk", "whisper", "shout", "laugh", "smile", "cry", "nod", "shake", "turn", "twist", "bend", "lean", "press", "strike", "hit", "kick", "cut", "break", "burn", "bleed", "hurt", "kill", "die", "live", "love", "hate", "fear", "hope", "wish", "want", "need", "try", "fail", "win", "lose", "fight", "guard", "protect", "attack", "defend", "escape", "hide", "seek", "search", "hunt", "chase", "catch", "grab", "seize", "steal", "buy", "sell", "pay", "owe", "trade", "weigh", "measure", "check", "test", "read", "write", "sign", "mark", "note", "answer", "reply", "agree", "refuse", "accept", "offer", "promise", "swear", "trust", "doubt", "believe", "remember", "forget", "notice", "consider", "decide", "choose", "prefer", "expect", "suppose", "imagine", "wonder", "guess", "assume", "pretend", "manage", "handle", "deal", "settle", "arrange", "prepare", "plan", "gather", "collect", "spread", "scatter", "cover", "fill", "empty", "pour", "wash", "clean", "dress", "wear", "remove", "return", "repeat", "continue", "finish", "complete", "end", "begin", "enter", "exit", "arrive", "depart", "travel", "ride", "drive", "sail", "fly", "swim", "walk", "march", "poison", "wound", "injure", "corrupt", "shock", "terrify", "trap", "force", "surround", "determine",
}
# Adjective / colour stems: their -ly forms are adverbs ("Suddenly"), but their -ing/-ed
# forms are not verbs, so "Harding" and "Redding" are left alone.
_ADJECTIVE_STEMS = {
    "sudden", "careful", "quick", "slow", "quiet", "soft", "loud", "gentle", "calm", "immediate", "natural", "fortunate", "unfortunate", "clear", "obvious", "final", "actual", "real", "certain", "probab", "usual", "especial", "particular", "absolute", "exact", "simp", "mere", "bare", "hard", "near", "sharp", "swift", "eager", "bitter", "warm", "dark", "bright", "deep", "faint", "firm", "fierce", "grim", "harsh", "heavy", "rough", "smooth", "steady", "strange", "strong", "weak", "wild", "wide", "brief", "direct", "entire", "fair", "free", "full", "ready", "vague", "eventual", "ultimate", "apparent", "evident", "genuine", "honest", "plain", "polite", "proper", "rapid", "rare", "recent", "serious", "severe", "slight", "sole", "total", "utter", "violent", "visib", "whole", "silent", "dead", "cold", "light", "red", "blue", "green", "white", "black", "gold", "grey", "gray", "brown",
}


__all__ = ["NON_NAME_WORDS", "STOP_WORDS", "content_terms", "is_non_name_word", "stem", "tokenize_words"]
