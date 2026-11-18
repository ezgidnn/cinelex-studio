import os
import json
import re
import httpx
import requests
import urllib3
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
from dotenv import load_dotenv
from kelime_secici import hedef_kelimeyi_bul

urllib3.disable_warnings()
eski_request = requests.Session.request
def yeni_request(self, *a, **kw):
    kw["verify"] = False
    return eski_request(self, *a, **kw)
requests.Session.request = yeni_request

mevcut_klasor = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(mevcut_klasor, ".env"))

uygulama = FastAPI(title="CineLex Studio Sunucusu")

uygulama.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_anahtari = os.getenv("GROQ_API_KEY", "").strip()
groq_istemcisi = None
if groq_anahtari and "buraya_groq" not in groq_anahtari:
    groq_istemcisi = Groq(
        api_key=groq_anahtari,
        http_client=httpx.Client(verify=False)
    )

kelime_onbellegi = {
    "gonna": {"ana": "-ecek / -acak", "diger": ["going to (kısaltma)"]},
    "wanna": {"ana": "istemek", "diger": ["want to (kısaltma)"]},
    "gotta": {"ana": "zorunda olmak", "diger": ["got to (kısaltma)"]},
    "the": {"ana": "(belirli tanımlık)", "diger": ["o, bu, şu"]},
    "a": {"ana": "bir", "diger": ["herhangi bir"]},
    "an": {"ana": "bir", "diger": ["herhangi bir"]},
    "some": {"ana": "biraz / bazı", "diger": ["birkaç", "bir miktar"]}
}

# Sabit ve ultra hızlı CEFR kelime havuzu (A2 ve B1 kelimeleri kelime_secici.py'den gelir)
SEVIYE_KELIME_HAVUZU = {
    "A1": {
        "always", "animal", "answer", "arrive", "beautiful", "because", "before", "begin",
        "believe", "between", "birthday", "breakfast", "brother", "build", "business", "carry",
        "change", "cheap", "children", "choose", "clean", "clear", "close", "clothes", "coffee",
        "color", "company", "complete", "computer", "country", "course", "daughter", "decide",
        "different", "difficult", "dinner", "doctor", "dollar", "drink", "drive", "early",
        "easy", "eight", "enjoy", "enough", "evening", "every", "example", "excited", "exercise",
        "expensive", "explain", "family", "famous", "father", "favorite", "finish", "flower",
        "follow", "forget", "friend", "future", "garden", "glass", "goodbye", "great", "group",
        "happen", "happy", "health", "heavy", "hello", "history", "holiday", "hospital", "hotel",
        "house", "hundred", "hungry", "husband", "important", "include", "inside", "instead",
        "interesting", "internet", "island", "jacket", "kitchen", "language", "large", "laugh",
        "learn", "leave", "lesson", "letter", "library", "listen", "little", "machine", "market",
        "married", "matter", "maybe", "meaning", "message", "minute", "mistake", "modern",
        "moment", "money", "month", "morning", "mother", "mountain", "movie", "music", "nature",
        "never", "newspaper", "night", "nothing", "number", "office", "often", "outside", "paper",
        "parent", "party", "people", "person", "phone", "picture", "piece", "place", "plane",
        "plant", "please", "pocket", "police", "popular", "possible", "practice", "present",
        "pretty", "price", "problem", "promise", "question", "quick", "quiet", "radio", "ready",
        "really", "reason", "remember", "repeat", "restaurant", "return", "right", "river",
        "school", "science", "second", "secret", "sentence", "several", "shirt", "shoes", "short",
        "sister", "sleep", "small", "smile", "sometimes", "sorry", "sound", "speak", "special",
        "spend", "sport", "spring", "start", "station", "story", "street", "student", "study",
        "subject", "summer", "sunday", "supermarket", "sure", "surprise", "sweet", "table",
        "teach", "teacher", "thank", "thing", "think", "thirsty", "thousand", "ticket", "tired",
        "today", "together", "tomorrow", "tonight", "tooth", "town", "train", "travel", "tree",
        "trouble", "under", "understand", "university", "until", "usually", "vacation", "vegetable",
        "village", "visit", "wait", "walk", "watch", "water", "weather", "website", "weekend",
        "welcome", "window", "winter", "woman", "wonderful", "world", "worry", "write", "wrong",
        "yellow", "yesterday", "young"
    },
    "B2": {
        "accomplish", "accurate", "acknowledge", "acquire", "adapt", "adequate", "adjust",
        "admire", "admit", "advance", "affair", "afford", "ambitious", "analyze", "annoy",
        "anxious", "apparent", "appreciate", "approach", "appropriate", "approve", "argue",
        "arise", "arrange", "artificial", "ashamed", "aspect", "assess", "assist", "assume",
        "assure", "attach", "attempt", "attitude", "attract", "authority", "available",
        "aware", "awkward", "barely", "barrier", "behavior", "belief", "beneath", "benefit",
        "betray", "blame", "bother", "boundary", "brilliant", "burden", "capable", "capacity",
        "capture", "cautious", "challenge", "characteristic", "circumstance", "claim",
        "clarify", "collapse", "combine", "comfort", "command", "comment", "commit",
        "communicate", "community", "compare", "compete", "complain", "complex", "complicated",
        "concentrate", "concept", "concern", "conclude", "condition", "conduct", "confess",
        "confidence", "confirm", "conflict", "confuse", "consequence", "consider", "consist",
        "constant", "construct", "consume", "contact", "contain", "contemporary", "content",
        "context", "contrast", "contribute", "convince", "cope", "corporate", "courage",
        "crucial", "curious", "current", "damage", "debate", "decade", "deceive", "declare",
        "decline", "decorate", "decrease", "defend", "define", "definite", "delay",
        "deliberate", "delicate", "deliver", "demand", "demonstrate", "deny", "depend",
        "depressed", "deserve", "desperate", "despite", "destroy", "determine", "develop",
        "device", "devote", "differ", "dignity", "dilemma", "dimension", "diminish",
        "disappoint", "disaster", "discipline", "discover", "discuss", "disgust", "dismiss",
        "display", "dispute", "distant", "distinct", "distinguish", "distract", "distribute",
        "disturb", "diverse", "domestic", "dominate", "doubt", "dramatic", "eager", "economy",
        "educate", "efficient", "effort", "elaborate", "elderly", "elect", "element",
        "eliminate", "embarrass", "emerge", "emotion", "emphasis", "emphasize", "enable",
        "encounter", "encourage", "endure", "engage", "enhance", "enormous", "ensure",
        "entertain", "enthusiasm", "entire", "entitle", "environment", "episode", "equal",
        "equip", "equivalent", "error", "escape", "essential", "establish", "estimate",
        "evaluate", "eventually", "evidence", "evil", "evolve", "examine", "exceed",
        "excellent", "exception", "excessive", "exchange", "excite", "exclude", "excuse",
        "execute", "exhaust", "exhibit", "exist", "expand", "expect", "expense", "experience",
        "experiment", "expert", "explain", "explicit", "explode", "exploit", "explore",
        "expose", "express", "extend", "extensive", "extent", "external", "extraordinary",
        "extreme", "facility", "factor", "fade", "failure", "faint", "fair", "faith",
        "familiar", "fascinate", "fashion", "fatal", "fault", "favor", "fear", "feature",
        "federal", "fee", "feedback", "fellow", "fierce", "figure", "finance", "flexible",
        "float", "flood", "flourish", "focus", "forbid", "force", "forecast", "foreign",
        "forgive", "formal", "former", "fortunate", "foundation", "fragile", "frame",
        "frankly", "frequent", "frighten", "frustrate", "fulfill", "function", "fundamental",
        "furious", "furthermore", "gain", "gather", "generate", "generous", "genius",
        "genuine", "gesture", "glance", "global", "glory", "grab", "grace", "gradual",
        "grant", "grateful", "guarantee", "guilty", "habit", "handle", "harm", "harsh",
        "hesitate", "highlight", "hire", "honest", "honor", "horrible", "hostile", "humble",
        "humor", "hypothesis", "identical", "identify", "ignore", "illegal", "illustrate",
        "image", "imagine", "immediate", "immense", "impact", "implement", "imply", "impose",
        "impress", "improve", "incident", "include", "income", "increase", "incredible",
        "independent", "indicate", "individual", "induce", "inevitable", "infect", "infer",
        "infinite", "influence", "inform", "initial", "initiative", "injure", "innocent",
        "innovate", "input", "inquire", "insight", "insist", "inspect", "inspire", "install",
        "instance", "instant", "instinct", "institute", "instruct", "instrument", "insult",
        "insurance", "integrate", "intellectual", "intelligence", "intend", "intense",
        "interact", "interest", "interfere", "internal", "interpret", "interrupt", "interval",
        "intervene", "intimate", "introduce", "invade", "invent", "invest", "investigate",
        "involve", "isolate", "issue", "jealous", "joint", "journal", "journey", "judge",
        "justice", "justify", "keen", "label", "labor", "lack", "landscape", "launch",
        "layer", "lecture", "legal", "leisure", "liberty", "license", "limit", "link",
        "literature", "locate", "logic", "loyal", "luxury", "maintain", "major", "manage",
        "manipulate", "manner", "manufacture", "margin", "massive", "master", "mature",
        "maximum", "meanwhile", "measure", "mechanism", "media", "mental", "mention",
        "merely", "method", "migrate", "military", "minimum", "minor", "miracle", "mislead",
        "mission", "mistake", "mixture", "moderate", "modern", "modest", "modify", "monitor",
        "moral", "moreover", "motive", "mount", "multiple", "murder", "mutual", "mystery",
        "narrow", "native", "neat", "necessary", "negative", "neglect", "negotiate", "nervous",
        "network", "neutral", "nevertheless", "noble", "nonsense", "normal", "notable",
        "notice", "notion", "nuclear", "numerous", "obey", "object", "objective", "oblige",
        "observe", "obsess", "obtain", "obvious", "occasion", "occupy", "occur", "odd",
        "offend", "offer", "official", "operate", "opinion", "opponent", "opportunity",
        "oppose", "optimistic", "option", "ordinary", "organize", "origin", "outcome",
        "outline", "output", "outstanding", "overcome", "overlook", "overseas", "owe",
        "panic", "parallel", "participate", "particular", "partly", "passion", "passive",
        "patience", "pattern", "pause", "peculiar", "penalty", "perceive", "percent",
        "perform", "permanent", "permission", "permit", "persist", "personal", "persuade",
        "phenomenon", "philosophy", "physical", "pioneer", "plain", "pleasant", "pleasure",
        "plenty", "policy", "polite", "political", "pollute", "popular", "portion", "pose",
        "position", "positive", "possess", "potential", "poverty", "practical", "praise",
        "predict", "prefer", "prejudice", "prepare", "presence", "preserve", "pressure",
        "pretend", "prevent", "previous", "pride", "primary", "principal", "principle",
        "priority", "privacy", "privilege", "probable", "procedure", "proceed", "process",
        "produce", "profession", "profit", "profound", "progress", "prohibit", "project",
        "prominent", "promise", "promote", "prompt", "proof", "proper", "property",
        "proportion", "propose", "prospect", "protect", "protest", "proud", "prove",
        "provide", "provoke", "psychological", "publish", "punish", "purchase", "pure",
        "purpose", "pursue", "qualify", "quality", "quantity", "quarrel", "quote", "radical",
        "random", "range", "rapid", "rare", "rational", "react", "realistic", "reality",
        "realize", "reasonable", "recall", "recent", "recognize", "recommend", "recover",
        "reduce", "refer", "reflect", "reform", "refuse", "regard", "region", "register",
        "regret", "regular", "regulate", "reject", "relate", "relative", "relax", "release",
        "relevant", "reliable", "relief", "relieve", "reluctant", "rely", "remain", "remark",
        "remedy", "remind", "remote", "remove", "repair", "repeat", "replace", "reply",
        "report", "represent", "reputation", "request", "require", "rescue", "research",
        "resemble", "reserve", "resident", "resist", "resolve", "resort", "resource",
        "respect", "respond", "responsible", "restore", "restrict", "result", "retain",
        "retire", "retreat", "reveal", "revenge", "reverse", "review", "revise", "revolution",
        "reward", "ridiculous", "rigid", "risk", "rival", "romantic", "rough", "routine",
        "ruin", "rumor", "rural", "rush", "sacrifice", "satisfy", "scandal", "scare",
        "scatter", "schedule", "scheme", "scholar", "scope", "scratch", "scream", "secure",
        "seek", "seize", "select", "selfish", "senior", "sensible", "sensitive", "separate",
        "sequence", "series", "serious", "serve", "session", "settle", "severe", "shadow",
        "shallow", "shame", "shape", "share", "sharp", "shelter", "shift", "shock", "shortage",
        "shrink", "sigh", "significant", "silly", "similar", "sincere", "situate", "skill",
        "slight", "slip", "smooth", "social", "society", "solid", "solution", "solve",
        "sophisticated", "source", "spare", "specific", "spectacular", "speech", "spirit",
        "spite", "split", "spoil", "spread", "squeeze", "stable", "stage", "standard",
        "stare", "statement", "status", "steady", "steal", "steep", "stick", "stiff",
        "stimulate", "stock", "strategy", "strength", "stress", "stretch", "strict", "strike",
        "struggle", "stubborn", "studio", "stuff", "stumble", "subject", "submit",
        "substantial", "substitute", "subtle", "succeed", "sudden", "suffer", "sufficient",
        "suggest", "suitable", "summarize", "superior", "supply", "support", "suppose",
        "surface", "surgery", "surprise", "surround", "survey", "survive", "suspect",
        "suspend", "sustain", "swallow", "swear", "sweep", "symbol", "sympathy", "symptom",
        "system", "tackle", "talent", "target", "task", "temper", "temporary", "tempt",
        "tendency", "tension", "terminal", "terrible", "territory", "terror", "theme",
        "theory", "therapy", "therefore", "thorough", "threat", "thrill", "throughout",
        "tiny", "tolerate", "topic", "torture", "total", "tough", "trace", "track",
        "tradition", "tragedy", "transfer", "transform", "transition", "translate",
        "transmit", "transparent", "transport", "trap", "treasure", "treat", "tremendous",
        "trend", "trial", "trick", "trigger", "triumph", "trouble", "trust", "truth",
        "typical", "ugly", "ultimate", "unbelievable", "unconscious", "undergo", "underlying",
        "undertake", "unfortunate", "uniform", "unique", "unite", "universal", "unlikely",
        "unusual", "update", "upset", "urban", "urge", "urgent", "vague", "valid", "valuable",
        "value", "vanish", "variable", "variety", "various", "vast", "vehicle", "version",
        "victim", "victory", "view", "violate", "violent", "virtual", "virtue", "visible",
        "vision", "vital", "vivid", "vocabulary", "volume", "voluntary", "volunteer",
        "vulnerable", "wander", "warn", "waste", "wealth", "weapon", "weird", "welfare",
        "whereas", "whereby", "whisper", "widespread", "willing", "wisdom", "withdraw",
        "witness", "wonder", "worth", "wound", "wrap", "wreck", "yield", "youth", "zone"
    },
    "C1": {
        "abolish", "abrupt", "absurd", "abundance", "accelerate", "accessible", "accommodate",
        "accountable", "accumulate", "accusation", "acute", "addiction", "adhere", "adjacent",
        "advocate", "aesthetic", "affection", "aggregate", "albeit", "align", "allegation",
        "allocate", "ambiguity", "ambiguous", "amend", "analogy", "anonymous", "anticipate",
        "apparatus", "appealing", "arbitrary", "archive", "articulate", "aspiration",
        "assemble", "assert", "asset", "assign", "assimilate", "atrocity", "attain",
        "attribute", "authentic", "autonomy", "backlash", "beneficial", "benevolent",
        "bias", "bizarre", "blatant", "bleak", "breakthrough", "breed", "brutal", "bureaucracy",
        "candid", "catastrophe", "cease", "chronic", "clarity", "coincide", "collaborate",
        "commence", "commodity", "compelling", "compensate", "competent", "compile",
        "complement", "comply", "comprehensive", "comprise", "compulsory", "conceal",
        "concede", "conceive", "condemn", "confer", "confine", "conform", "confront",
        "consensus", "consent", "consolidate", "conspiracy", "constitute", "constrain",
        "contemplate", "contempt", "contend", "contradict", "controversial", "conventional",
        "convey", "conviction", "cooperate", "correlate", "corrupt", "counterpart", "credible",
        "cultivate", "cumulative", "cynical", "debris", "deceit", "decisive", "dedicate",
        "deduce", "deficient", "defy", "degenerate", "deliberately", "denounce", "depict",
        "deplete", "deploy", "deprive", "derive", "designate", "deteriorate", "devastate",
        "deviate", "devise", "diagnose", "dictate", "diminish", "diplomatic", "disclose",
        "discourse", "discretion", "discriminate", "displace", "dispose", "disrupt",
        "distort", "divert", "doctrine", "domain", "drastic", "dubious", "duplicate",
        "dynamic", "eccentric", "ecological", "eligible", "eloquent", "embrace", "empirical",
        "enact", "encompass", "endeavor", "endorse", "enforce", "enlighten", "enrich",
        "ensue", "enterprise", "entity", "envisage", "epidemic", "equity", "eradicate",
        "erratic", "escalate", "essence", "eternal", "ethical", "evade", "evoke", "exaggerate",
        "excerpt", "exempt", "exert", "exile", "exotic", "expedition", "expertise", "explicitly",
        "extract", "fabricate", "facilitate", "fallacy", "feasible", "flaw", "fluctuate",
        "formulate", "foster", "franchise", "fraud", "friction", "futile", "graceful",
        "grief", "grim", "gross", "guerrilla", "hamper", "harass", "hazard", "hierarchy",
        "hinder", "hostility", "humanitarian", "hypocrisy", "ideology", "ignorance", "illusion",
        "imminent", "immune", "impair", "impartial", "imperative", "implicit", "incentive",
        "inclined", "incorporate", "indigenous", "indispensable", "indulge", "inequality",
        "inflict", "infrastructure", "inherent", "inhibit", "initiate", "inject", "inmate",
        "innate", "integrity", "intensify", "interim", "intricate", "intrigue", "intrinsic",
        "intuition", "invoke", "ironic", "irrelevant", "irreversible", "jeopardize", "judicial",
        "jurisdiction", "keenly", "legacy", "legitimate", "lethal", "liability", "liberal",
        "linger", "literacy", "lucrative", "magnitude", "mainstream", "malicious", "mandate",
        "manifest", "marginal", "medieval", "meditate", "melancholy", "memoir", "menace",
        "merge", "metaphor", "meticulous", "militant", "minimize", "momentum", "monopoly",
        "mortality", "municipal", "naive", "narrative", "nasty", "negligible", "notorious",
        "novelty", "nuance", "nurture", "obsession", "obsolete", "obstacle", "offspring",
        "ominous", "ongoing", "opaque", "oppression", "optimum", "orchestrate", "orientation",
        "orthodox", "outbreak", "outcry", "overhaul", "overwhelm", "paradox", "parameter",
        "partisan", "patent", "patron", "peculiarity", "peer", "penetrate", "perpetual",
        "persecute", "persistent", "perspective", "pessimistic", "petition", "plausible",
        "pledge", "plight", "ponder", "postpone", "practitioner", "pragmatic", "precaution",
        "precede", "precise", "predator", "predecessor", "predominant", "premise", "prescribe",
        "prestige", "presume", "prevail", "prevalent", "primitive", "proclaim", "procurement",
        "proficient", "profoundly", "prolong", "propaganda", "prosecute", "prospective",
        "protocol", "provincial", "provision", "prudence", "publicity", "pulse", "query",
        "quest", "quota", "ratify", "realm", "rebellion", "recession", "recipient",
        "reciprocal", "reckless", "reconcile", "recur", "redundant", "refuge", "regime",
        "reinforce", "relentless", "reminiscent", "render", "renounce", "renowned", "repercussion",
        "replicate", "repress", "reproduce", "resent", "reside", "resilience", "respective",
        "restraint", "resume", "retaliate", "retrieve", "revelation", "revenue", "revive",
        "rhetoric", "rigorous", "robust", "ruthless", "sabotage", "sacred", "sanction",
        "sarcastic", "saturate", "scarcity", "skeptical", "scrutiny", "secular", "segment",
        "sentiment", "sheer", "shrewd", "simulate", "simultaneous", "skepticism",
        "sovereign", "spark", "speculate", "spontaneous", "stabilize", "stagnant", "stark",
        "statute", "stereotype", "stigma", "stipulate", "strategic", "strive", "subordinate",
        "subsequent", "subsidy", "subtlety", "successor", "suffice", "suppress",
        "surge", "surplus", "surveillance", "susceptible", "symbolic", "syndrome", "synthesis",
        "tactic", "tangible", "tedious", "tentative", "terminate", "testify",
        "threshold", "thrive", "toll", "trait", "transaction", "transcend", "trauma",
        "treaty", "trivial", "turmoil", "tyranny", "unanimous", "uncanny", "undermine",
        "unfold", "unprecedented", "unravel", "uphold", "utility", "utopia", "validate",
        "venture", "verdict", "verify", "versatile", "viable", "vicinity", "vicious",
        "vindicate", "violation", "virtually", "volatile", "warrant", "weary", "whimsical",
        "withstand", "zeal"
    },
    "C2": {
        "aberration", "abhor", "abstruse", "acumen", "adamant", "admonish", "aesthetic",
        "alacrity", "alleviate", "amalgamate", "ameliorate", "anachronism", "anathema",
        "animosity", "antithesis", "apathy", "appease", "arcane", "arduous", "assiduous",
        "astute", "auspicious", "avarice", "belligerent", "benevolence", "benign", "cacophony",
        "cajole", "callous", "capricious", "castigate", "catharsis", "caustic", "chicanery",
        "circumspect", "clairvoyant", "coalesce", "cogent", "commensurate", "compendium",
        "complacent", "concomitant", "conflagration", "conundrum", "copious", "corroborate",
        "credulous", "cryptic", "culpable", "cursory", "dearth", "debacle", "decorum",
        "deference", "deleterious", "demagogue", "denigrate", "despot", "diatribe", "dichotomy",
        "diffident", "dilatory", "disparate", "dissemble", "ebullient", "eclectic", "edify",
        "efficacious", "effrontery", "egregious", "elucidate", "emulate", "enervate", "enigma",
        "ephemeral", "equanimity", "equivocal", "erudite", "esoteric", "euphemism", "exacerbate",
        "exculpate", "execrable", "exhort", "exonerate", "expedient", "extol", "extraneous",
        "facetious", "fastidious", "fatuous", "fecund", "felicitous", "flagrant", "fortuitous",
        "fractious", "garrulous", "gregarious", "hackneyed", "harangue", "hegemony", "iconoclast",
        "idiosyncrasy", "ignominious", "immutable", "impecunious", "impervious", "impetuous",
        "implacable", "inanity", "inchoate", "incisive", "incontrovertible", "indefatigable",
        "ineffable", "inexorable", "ingenuous", "inimical", "iniquity", "insidious", "insipid",
        "intransigent", "inundate", "invective", "irascible", "juxtapose", "laconic", "languid",
        "legerdemain", "loquacious", "lucid", "lugubrious", "magnanimous", "malinger", "malleable",
        "mendacious", "mercurial", "misanthrope", "mitigate", "mollify", "morose", "mundane",
        "munificent", "myriad", "nefarious", "neophyte", "obdurate", "obfuscate", "obsequious",
        "obstreperous", "obtuse", "onerous", "ostentatious", "ostracize", "palliate", "panacea",
        "paradigm", "paragon", "parsimonious", "pedantic", "penchant", "penurious", "pernicious",
        "perspicacious", "pertinacious", "phlegmatic", "platitude", "plethora", "polemic",
        "precipitate", "preclude", "precocious", "predilection", "prevaricate", "proclivity",
        "profligate", "propensity", "propitious", "punctilious", "quagmire", "querulous",
        "quixotic", "rancor", "recalcitrant", "recondite", "redoubtable", "refulgent", "relegate",
        "remonstrate", "reprobate", "repudiate", "rescind", "reticent", "sagacious", "salient",
        "sanctimonious", "sanguine", "scurrilous", "serendipity", "solicitous", "spurious",
        "staid", "stoic", "strident", "supercilious", "surreptitious", "sycophant", "taciturn",
        "temerity", "tenacious", "timorous", "torpid", "trenchant", "truculent", "ubiquitous",
        "umbrage", "unctuous", "usurp", "vacillate", "venerable", "veracity", "verbose",
        "vexation", "vicarious", "vilify", "vitriolic", "vociferous", "zealous"
    }
}

YAYGIN_KALIPLAR = {
    "sort of": {"ana": "bir nevi / gibi", "diger": ["bir bakıma", "türden"]},
    "kind of": {"ana": "bir nevi / gibi", "diger": ["biraz", "sayılır"]},
    "do justice": {"ana": "hakkını vermek", "diger": ["layığıyla göstermek"]},
    "figure out": {"ana": "çözmek / anlamak", "diger": ["hesaplamak"]},
    "find out": {"ana": "öğrenmek / keşfetmek", "diger": ["ortaya çıkarmak"]},
    "give up": {"ana": "vazgeçmek / bırakmak", "diger": ["pes etmek"]},
    "end up": {"ana": "sonunda ... olmak", "diger": ["kendini ... bulmak"]},
    "used to": {"ana": "eskiden ... yapardı", "diger": ["alışkın olmak"]},
    "make sense": {"ana": "mantıklı gelmek", "diger": ["anlam ifade etmek"]},
    "take care of": {"ana": "ilgilenmek / bakmak", "diger": ["halletmek"]},
    "get rid of": {"ana": "kurtulmak", "diger": ["başından atmak"]},
    "look forward to": {"ana": "dört gözle beklemek", "diger": []},
    "in the middle of": {"ana": "tam ortasında", "diger": ["meşgul olmak"]},
    "right away": {"ana": "hemen / derhal", "diger": ["anında"]},
    "at least": {"ana": "en azından", "diger": ["hiç olmazsa"]},
    "as well": {"ana": "de / da / ayrıca", "diger": ["bunun yanı sıra"]},
    "by the way": {"ana": "bu arada", "diger": ["sırası gelmişken"]},
    "for sure": {"ana": "kesinlikle", "diger": ["elbette"]},
    "no matter": {"ana": "fark etmez / ne olursa olsun", "diger": []},
    "turn out": {"ana": "ortaya çıkmak / dönüşmek", "diger": ["sonuçlanmak"]},
    "work out": {"ana": "çözülmek / yoluna girmek", "diger": ["spor yapmak"]},
    "hang out": {"ana": "takılmak / vakit geçirmek", "diger": []},
    "come up with": {"ana": "bulmak / üretmek (fikir)", "diger": []},
    "put up with": {"ana": "katlanmak / tahammül etmek", "diger": []},
    "run out of": {"ana": "tükenmek / bitmek", "diger": []},
    "catch up": {"ana": "yetişmek / arayı kapatmak", "diger": []},
    "show up": {"ana": "ortaya çıkmak / gelmek", "diger": []},
    "break up": {"ana": "ayrılmak", "diger": ["dağılmak"]},
    "get over": {"ana": "atlatmak / üstesinden gelmek", "diger": []},
    "point out": {"ana": "belirtmek / işaret etmek", "diger": []},
    "carry on": {"ana": "devam etmek", "diger": ["sürdürmek"]},
    "calm down": {"ana": "sakinleşmek", "diger": []},
    "cheer up": {"ana": "neşelenmek", "diger": []},
    "let down": {"ana": "hayal kırıklığına uğratmak", "diger": []},
    "look after": {"ana": "göz kulak olmak / bakmak", "diger": []},
    "look up to": {"ana": "saygı duymak / örnek almak", "diger": []},
    "make up": {"ana": "uydurmak / barışmak", "diger": ["oluşturmak"]},
    "set up": {"ana": "kurmak / ayarlamak", "diger": []},
    "take off": {"ana": "çıkarmak / havalanmak", "diger": []},
    "turn down": {"ana": "geri çevirmek / kısmak", "diger": []}
}

class VideoIstegi(BaseModel):
    youtube_linki: str
    seviye_filtresi: Optional[str] = "B1_B2"

class TekKelimeIstegi(BaseModel):
    kelime: str
    cumle: Optional[str] = ""

def video_id_ayikla(link: str) -> str:
    desen = r"(?:v=|\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})"
    eslesme = re.search(desen, link)
    if not eslesme:
        raise ValueError("Geçersiz YouTube linki girdiniz.")
    return eslesme.group(1)

def cumleleri_ayir(ham_parcalar: list) -> list:
    atomik_parcalar = []
    for p in ham_parcalar:
        metin = p["metin"]
        if not metin or metin.startswith("[") or metin.startswith("("):
            continue

        parca_cumleler = [c.strip() for c in re.split(r'(?<=[.?!])\s+', metin) if c.strip()]
        if len(parca_cumleler) <= 1:
            atomik_parcalar.append(p)
        else:
            toplam_harf = max(1, sum(len(c) for c in parca_cumleler))
            toplam_sure = max(0.3, p["bitis"] - p["baslangic"])
            imlec = p["baslangic"]
            for idx, c in enumerate(parca_cumleler):
                pay = (len(c) / toplam_harf) * toplam_sure
                bitis = p["bitis"] if idx == len(parca_cumleler) - 1 else round(imlec + pay, 2)
                atomik_parcalar.append({
                    "baslangic": round(imlec, 2),
                    "bitis": bitis,
                    "metin": c
                })
                imlec = bitis

    tek_cumleler = []
    aktif = None

    for p in atomik_parcalar:
        if aktif is None:
            aktif = {
                "baslangic": p["baslangic"],
                "bitis": p["bitis"],
                "metin": p["metin"],
                "parcalar": [dict(p)]
            }
        else:
            onceki_bitti = aktif["metin"].endswith((".", "?", "!"))
            bosluk = p["baslangic"] - aktif["bitis"]
            kelime_sayisi = len(aktif["metin"].split())

            if onceki_bitti or bosluk > 1.4 or kelime_sayisi >= 22:
                tek_cumleler.append(aktif)
                aktif = {
                    "baslangic": p["baslangic"],
                    "bitis": p["bitis"],
                    "metin": p["metin"],
                    "parcalar": [dict(p)]
                }
            else:
                aktif["metin"] += " " + p["metin"]
                aktif["bitis"] = max(aktif["bitis"], p["bitis"])
                aktif["parcalar"].append(dict(p))

    if aktif:
        tek_cumleler.append(aktif)

    for i in range(len(tek_cumleler) - 1):
        sonraki_bas = tek_cumleler[i + 1]["baslangic"]
        if sonraki_bas > tek_cumleler[i]["bitis"] and (sonraki_bas - tek_cumleler[i]["bitis"]) < 3.0:
            tek_cumleler[i]["bitis"] = sonraki_bas

    return tek_cumleler

def altyazilari_cek(video_id: str) -> list:
    yt_api = YouTubeTranscriptApi()
    if hasattr(yt_api, "fetch"):
        ham_veri = yt_api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        ham_parcalar = [
            {
                "baslangic": round(s.start, 2),
                "bitis": round(s.start + s.duration, 2),
                "metin": re.sub(r"\s+", " ", s.text).strip()
            }
            for s in ham_veri
        ]
    else:
        ham_veri = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        ham_parcalar = [
            {
                "baslangic": round(s["start"], 2),
                "bitis": round(s["start"] + s["duration"], 2),
                "metin": re.sub(r"\s+", " ", s["text"]).strip()
            }
            for s in ham_veri
        ]

    return cumleleri_ayir(ham_parcalar)

def havuzdan_kelime_bul(cumle: str, seviye: str):
    """Sabit A1 / B2 / C1 / C2 kümelerinden milisaniyede kelime yakalar."""
    kume = SEVIYE_KELIME_HAVUZU.get(seviye)
    if not kume:
        return None, None
    kelimeler = re.findall(r"\b[a-zA-Z]{4,}\b", cumle)
    for k in kelimeler:
        if k.lower() in kume:
            return k, seviye
    return None, None

def gruptan_kelime_bul(cumle: str, grup: str):
    """Seçilen 2'li seviye grubu içindeki (A1-A2, B1-B2 veya C1-C2) kelimeleri arar."""
    if grup == "C1_C2":
        for sev in ("C2", "C1"):
            k, s = havuzdan_kelime_bul(cumle, sev)
            if k:
                return k, s
        return None, None

    if grup == "B1_B2":
        k, s = havuzdan_kelime_bul(cumle, "B2")
        if k:
            return k, s
        return hedef_kelimeyi_bul(cumle, "B1")

    if grup == "A1_A2":
        k, s = hedef_kelimeyi_bul(cumle, "A2")
        if k:
            return k, s
        return havuzdan_kelime_bul(cumle, "A1")

    return None, None

def google_sozluk_detayli(kelime: str) -> dict:
    temiz = kelime.lower().strip()
    if temiz in kelime_onbellegi:
        return kelime_onbellegi[temiz]
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "tr",
                "dt": ["t", "bd"],
                "q": temiz
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=2
        )
        veri = r.json()
        anlamlar = []
        if len(veri) > 1 and veri[1]:
            for grup in veri[1][:3]:
                for sozcuk in grup[1][:3]:
                    w = sozcuk.lower().strip()
                    if w and w not in anlamlar:
                        anlamlar.append(w)
        if veri[0] and veri[0][0] and veri[0][0][0]:
            ana = veri[0][0][0].lower().strip()
            if ana and ana not in anlamlar:
                anlamlar.insert(0, ana)

        ana_anlam = anlamlar[0] if anlamlar else "—"
        diger_anlamlar = anlamlar[1:4]
        sonuc = {"ana": ana_anlam, "diger": diger_anlamlar}
        kelime_onbellegi[temiz] = sonuc
        return sonuc
    except Exception as e:
        print("Sözlük hatası:", e)
        return {"ana": "—", "diger": []}

def cumlede_kalip_bul(kelime: str, cumle: str) -> Optional[dict]:
    if not cumle:
        return None
    temiz_cumle = re.sub(r"[^a-zA-Z'\s-]", " ", cumle.lower())
    temiz_cumle = re.sub(r"\s+", " ", temiz_cumle).strip()

    for kalip, ceviri in YAYGIN_KALIPLAR.items():
        if re.search(rf"\b{re.escape(kalip)}\b", temiz_cumle):
            kalip_kelimeleri = kalip.split()
            if kelime in kalip_kelimeleri:
                return {
                    "ifade": kalip,
                    "ana": ceviri["ana"],
                    "diger": ceviri["diger"]
                }
    return None

def turkce_anlamlari_getir(sorular: list) -> dict:
    if not sorular:
        return {}

    if groq_istemcisi:
        try:
            satirlar = [
                f"{sira}. Cümle: \"{item['cumle']}\" | Hedef Kelime: \"{item['hedef_kelime']}\""
                for sira, item in enumerate(sorular)
            ]
            komut = (
                "Aşağıdaki İngilizce repliklerde geçen hedef kelimelerin, "
                "SADECE o cümledeki bağlamına uygun kısa Türkçe karşılığını (1-3 kelime) yaz.\n"
                "Yanıtı yalnızca JSON formatında ver. Örnek: {\"0\": \"fondöten\", \"1\": \"başlamak\"}\n\n"
                + "\n".join(satirlar)
            )
            yanit = groq_istemcisi.chat.completions.create(
                messages=[{"role": "user", "content": komut}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            sonuc = json.loads(yanit.choices[0].message.content)
            if sonuc:
                return sonuc
        except Exception as e:
            print("Groq çeviri hatası (yedek sözlüğe geçiliyor):", e)

    sonuclar = {}
    for sira, item in enumerate(sorular):
        detay = google_sozluk_detayli(item["hedef_kelime"])
        sonuclar[str(sira)] = detay["ana"]
    return sonuclar

@uygulama.post("/kelime-cevir")
async def tek_kelime_cevir(istek: TekKelimeIstegi):
    temiz = re.sub(r"[^a-zA-Z'-]", "", istek.kelime).lower()
    if not temiz:
        return {"ana": "", "diger": [], "kalip": None}

    tekil = google_sozluk_detayli(temiz)
    kalip = cumlede_kalip_bul(temiz, istek.cumle)

    return {
        "ana": tekil["ana"],
        "diger": tekil["diger"],
        "kalip": kalip
    }

@uygulama.post("/video-hazirla")
async def video_hazirla(istek: VideoIstegi):
    try:
        video_id = video_id_ayikla(istek.youtube_linki)
        tam_cumleler = altyazilari_cek(video_id)
    except Exception as hata:
        raise HTTPException(status_code=400, detail=f"Altyazı çekilemedi: {str(hata)}")

    secilen_grup = istek.seviye_filtresi or "B1_B2"
    grup_onceligi = {
        "C1_C2": ["C1_C2", "B1_B2", "A1_A2"],
        "B1_B2": ["B1_B2", "A1_A2"],
        "A1_A2": ["A1_A2"]
    }
    denenecek_gruplar = grup_onceligi.get(secilen_grup, ["B1_B2", "A1_A2"])

    islenmis = []
    ceviri_bekleyenler = []

    for aktif_grup in denenecek_gruplar:
        islenmis = []
        ceviri_bekleyenler = []

        for satir in tam_cumleler:
            cumle = satir["metin"]
            hedef_kelime, seviye = gruptan_kelime_bul(cumle, aktif_grup)

            islenmis_parcalar = []
            kelime_gizlendi = False

            for p in satir["parcalar"]:
                p_metin = p["metin"]
                if hedef_kelime and not kelime_gizlendi and re.search(rf"\b{re.escape(hedef_kelime)}\b", p_metin):
                    p_bosluklu = re.sub(rf"\b{re.escape(hedef_kelime)}\b", "_____", p_metin, count=1)
                    kelime_gizlendi = True
                else:
                    p_bosluklu = p_metin
                islenmis_parcalar.append({
                    "baslangic": p["baslangic"],
                    "bitis": p["bitis"],
                    "tam_metin": p_metin,
                    "bosluklu_metin": p_bosluklu
                })

            veri = {
                "baslangic": satir["baslangic"],
                "bitis": satir["bitis"],
                "tam_cumle": cumle,
                "parcalar": islenmis_parcalar,
                "soru_var_mi": bool(hedef_kelime and kelime_gizlendi),
                "hedef_kelime": hedef_kelime if kelime_gizlendi else None,
                "seviye": seviye if kelime_gizlendi else None,
                "turkce_ipucu": None
            }

            if veri["soru_var_mi"]:
                ceviri_bekleyenler.append({
                    "liste_sirasi": len(islenmis),
                    "cumle": cumle,
                    "hedef_kelime": hedef_kelime
                })

            islenmis.append(veri)

        # Seçilen 2'li grupta videoda en az 1 kelime bulunduysa alt gruba düşmeden dur
        if len(ceviri_bekleyenler) > 0:
            break

    for bas in range(0, len(ceviri_bekleyenler), 20):
        grup = ceviri_bekleyenler[bas:bas + 20]
        ceviriler = turkce_anlamlari_getir(grup)
        for sira_str, tr_anlam in ceviriler.items():
            idx = int(sira_str)
            if idx < len(grup):
                ilgili_soru = grup[idx]
                islenmis[ilgili_soru["liste_sirasi"]]["turkce_ipucu"] = tr_anlam

    return {
        "video_id": video_id,
        "toplam_satir": len(islenmis),
        "soru_sayisi": len(ceviri_bekleyenler),
        "altyazilar": islenmis
    }

@uygulama.get("/")
async def ana_sayfa():
    mevcut_dizin = os.path.dirname(os.path.abspath(__file__))
    ayni_klasor_html = os.path.join(mevcut_dizin, "index.html")
    if os.path.exists(ayni_klasor_html):
        return FileResponse(ayni_klasor_html)
    ust_dizin = os.path.dirname(mevcut_dizin)
    return FileResponse(os.path.join(ust_dizin, "ekran-arayuzu", "index.html"))