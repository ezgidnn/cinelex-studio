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

# Tam Bağımsız A1 - C2 Kelime Havuzu
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
    "A2": {
        "ability", "abroad", "accept", "accident", "achieve", "across", "active", "activity",
        "actually", "addition", "address", "adult", "advantage", "adventure", "advertise",
        "advice", "affect", "afraid", "against", "agree", "ahead", "allow", "almost", "alone",
        "along", "already", "although", "amazing", "among", "amount", "ancient", "angry",
        "announce", "another", "anybody", "anymore", "anything", "anywhere", "apart", "apartment",
        "apologize", "appear", "apply", "appointment", "area", "argument", "army", "around",
        "article", "artist", "asleep", "attention", "audience", "author", "autumn", "average",
        "avoid", "awake", "award", "awful", "background", "balance", "basic", "battle", "beach",
        "beauty", "become", "behind", "belong", "below", "beside", "beyond", "bicycle", "billion",
        "blind", "block", "blood", "board", "borrow", "bottom", "brain", "branch", "brave",
        "break", "breath", "bridge", "bright", "bring", "broken", "budget", "burn", "bury",
        "button", "calendar", "camera", "cancel", "cancer", "candidate", "capital", "captain",
        "careful", "careless", "carpet", "cartoon", "castle", "catch", "cause", "celebrate",
        "center", "century", "certain", "certainly", "chance", "character", "charge", "check",
        "chemical", "choice", "church", "circle", "citizen", "classic", "clever", "climate",
        "climb", "clock", "cloud", "coach", "coast", "collect", "college", "comfortable",
        "common", "competition", "complaint", "completely", "condition", "connect", "consider",
        "continue", "control", "conversation", "cookie", "corner", "correct", "cost", "cotton",
        "cough", "count", "couple", "cousin", "cover", "crazy", "create", "crime", "criminal",
        "cross", "crowd", "crowded", "cruel", "culture", "customer", "daily", "danger",
        "dangerous", "dark", "death", "decision", "deep", "degree", "delicious", "department",
        "describe", "desert", "design", "detail", "diary", "dictionary", "difference", "direction",
        "dirty", "disappear", "discover", "disease", "dish", "distance", "divide", "double",
        "download", "downstairs", "drama", "dream", "dress", "drop", "during", "dust", "duty",
        "earth", "eastern", "effect", "either", "electric", "electricity", "elephant", "elevator",
        "else", "empty", "enemy", "energy", "engine", "engineer", "enormous", "enter", "entrance",
        "envelope", "environment", "especially", "euro", "event", "ever", "everyone", "everything",
        "everywhere", "exact", "exactly", "exam", "excellent", "except", "exchange", "exciting",
        "excuse", "expect", "experience", "experiment", "expert", "extra", "fact", "factory",
        "fail", "fall", "false", "familiar", "famous", "fantastic", "farm", "farmer", "fashion",
        "fast", "fault", "favorite", "feeling", "festival", "fever", "field", "fight", "fill",
        "final", "finally", "finger", "flight", "floor", "foreign", "forest", "forever", "form",
        "fortunately", "forward", "free", "freedom", "fresh", "fridge", "friendly", "frightened",
        "front", "fruit", "full", "funny", "furniture", "further", "gallery", "game", "garage",
        "garbage", "gate", "general", "generally", "generation", "gentle", "geography", "ghost",
        "giant", "gift", "goal", "gold", "golden", "government", "grade", "grammar", "grandchild",
        "grandfather", "grandmother", "grass", "ground", "grow", "guard", "guess", "guest",
        "guide", "guitar", "habit", "haircut", "half", "hall", "handle", "handsome", "happen",
        "hardly", "healthy", "heart", "heat", "height", "helpful", "hero", "hide", "high",
        "highway", "hill", "himself", "hobby", "hold", "hole", "homework", "honey", "hope",
        "horrible", "horror", "host", "however", "huge", "human", "humorous", "hunt", "hurry",
        "hurt", "idea", "identify", "illness", "imagination", "imagine", "immediately",
        "impossible", "improve", "include", "increase", "indeed", "independent", "industry",
        "information", "injury", "insect", "inside", "instead", "instruction", "instrument",
        "intelligent", "international", "interview", "introduce", "invitation", "invite", "iron",
        "issue", "item", "itself", "jewelry", "join", "joke", "journalist", "journey", "judge",
        "juice", "jump", "jungle", "keep", "keyboard", "kick", "kill", "kind", "king", "kiss",
        "knee", "knife", "knowledge", "lake", "lamp", "land", "laptop", "last", "late", "lately",
        "later", "lazy", "lead", "leader", "leaf", "least", "leather", "left", "lend", "length",
        "less", "level", "lie", "life", "lift", "light", "likely", "line", "lion", "list",
        "local", "lock", "lonely", "look", "loose", "lose", "lost", "loud", "loudly", "lovely",
        "low", "luck", "lucky", "luggage", "lunch", "magazine", "magic", "mail", "main",
        "mainly", "major", "majority", "make", "male", "manage", "manager", "manner", "many",
        "map", "mark", "marry", "material", "math", "matter", "meal", "mean", "meaning",
        "measure", "meat", "medicine", "medium", "meet", "meeting", "member", "memory", "mention",
        "menu", "mess", "metal", "meter", "method", "middle", "midnight", "might", "mile",
        "mind", "mine", "mirror", "miss", "missing", "mistake", "mix", "mobile", "model",
        "modern", "moment", "monkey", "month", "mood", "moon", "mostly", "motorcycle", "mount",
        "mouse", "mouth", "move", "movement", "much", "murder", "muscle", "museum", "musician",
        "myself", "mystery", "name", "narrow", "nation", "national", "natural", "nature",
        "nearly", "neat", "necessary", "neck", "need", "neighbor", "neighborhood", "neither",
        "nervous", "network", "news", "next", "nice", "noise", "noisy", "none", "normal",
        "normally", "north", "nose", "note", "notice", "novel", "nowhere", "nurse", "object",
        "ocean", "offer", "officer", "official", "oil", "once", "online", "only", "open",
        "opera", "operate", "opinion", "opposite", "option", "order", "ordinary", "organization",
        "organize", "original", "other", "otherwise", "ourselves", "outdoor", "outdoors",
        "owner", "pack", "package", "page", "pain", "paint", "painter", "painting", "pair",
        "palace", "pale", "pants", "paragraph", "parent", "park", "part", "particular",
        "partner", "pass", "passenger", "passport", "past", "path", "patient", "pattern",
        "peace", "peaceful", "pencil", "pepper", "percent", "perfect", "perform", "perhaps",
        "period", "permission", "person", "personal", "petrol", "pharmacy", "photo",
        "photograph", "photographer", "photography", "physical", "physics", "piano", "pick",
        "picnic", "pilot", "pink", "pity", "pizza", "plan", "planet", "plastic", "plate",
        "platform", "play", "player", "pleasant", "pleased", "pleasure", "plenty", "plus",
        "poem", "poet", "poetry", "point", "poison", "polite", "political", "politician",
        "politics", "pollution", "pool", "poor", "population", "port", "position", "positive",
        "possibility", "post", "poster", "potato", "pound", "pour", "power", "powerful",
        "practical", "prefer", "prepare", "president", "press", "pretty", "prevent", "previous",
        "primary", "prince", "princess", "print", "printer", "prison", "prisoner", "private",
        "prize", "probably", "process", "produce", "product", "profession", "professional",
        "professor", "program", "progress", "project", "pronounce", "pronunciation", "proper",
        "properly", "protect", "proud", "prove", "provide", "public", "publish", "pull",
        "punish", "pupil", "purple", "purpose", "push", "quality", "quantity", "quarter",
        "queen", "quietly", "quite", "quiz", "race", "railway", "rain", "raise", "range",
        "rapid", "rare", "rarely", "rather", "reach", "react", "read", "reader", "reading",
        "real", "realistic", "realize", "receive", "recent", "recently", "reception", "recipe",
        "recognize", "recommend", "record", "recording", "recover", "recycle", "reduce",
        "refer", "reflect", "refrigerator", "refuse", "regarding", "region", "regular",
        "regularly", "relation", "relationship", "relative", "relax", "relaxed", "relaxing",
        "reliable", "religion", "religious", "remain", "remind", "remote", "remove", "rent",
        "repair", "replace", "reply", "report", "reporter", "request", "require", "research",
        "reservation", "reserve", "resort", "respect", "responsible", "rest", "result",
        "retire", "review", "rich", "ride", "rider", "ring", "rise", "risk", "road", "robot",
        "rock", "role", "roof", "room", "round", "route", "routine", "royal", "rubbish",
        "rude", "rule", "runner", "running", "rush", "sadly", "safe", "safely", "safety",
        "sail", "sailing", "sailor", "salad", "salary", "sale", "salt", "same", "sand",
        "sandwich", "satisfied", "sauce", "save", "scared", "scary", "scene", "schedule",
        "scientist", "score", "screen", "search", "season", "seat", "secretary", "section",
        "security", "seem", "select", "self", "sell", "send", "sense", "separate", "series",
        "serious", "seriously", "serve", "server", "service", "session", "set", "setting",
        "settle", "shade", "shadow", "shake", "shall", "shame", "shape", "share", "sharp",
        "sheep", "sheet", "shelf", "shell", "shine", "shiny", "ship", "shock", "shocked",
        "shocking", "shoot", "shooting", "shop", "shopping", "shoulder", "shout", "show",
        "shower", "shut", "sick", "side", "sight", "sign", "signal", "signature", "silence",
        "silent", "silk", "silly", "silver", "similar", "simple", "simply", "since", "sing",
        "singer", "singing", "single", "sink", "site", "situation", "size", "skill", "skin",
        "skirt", "sky", "slice", "slide", "slight", "slightly", "slip", "slow", "slowly",
        "smart", "smell", "smoke", "smoking", "smooth", "snake", "snow", "soap", "soccer",
        "social", "society", "sock", "soft", "software", "soil", "soldier", "solid", "solution",
        "solve", "somebody", "someone", "something", "somewhere", "song", "soon", "sore",
        "sort", "soul", "soup", "source", "south", "southern", "space", "spare", "speaker",
        "speed", "spell", "spelling", "spicy", "spider", "spirit", "spoon", "spot", "spread",
        "square", "stadium", "staff", "stage", "stairs", "stamp", "stand", "standard", "star",
        "state", "statement", "stay", "steal", "step", "stick", "still", "stomach", "stone",
        "store", "storm", "straight", "strange", "stranger", "strategy", "stress", "stressed",
        "strict", "strike", "string", "strong", "structure", "studio", "stuff", "stupid",
        "style", "succeed", "success", "successful", "such", "sudden", "suddenly", "sugar",
        "suggest", "suggestion", "suit", "suitable", "suitcase", "support", "suppose", "surface",
        "surprised", "surprising", "surround", "survey", "survive", "sweater", "swim",
        "swimming", "switch", "symbol", "system", "tablet", "tail", "take", "talent",
        "talented", "talk", "tall", "taste", "tasty", "team", "technology", "teenager",
        "telephone", "television", "tell", "temperature", "tennis", "tent", "term", "terrible",
        "test", "text", "than", "theater", "themselves", "then", "there", "therefore", "thick",
        "thin", "thinking", "third", "though", "thought", "throat", "through", "throw", "thumb",
        "thunder", "thus", "tidy", "tie", "tiger", "tight", "till", "time", "timetable", "tiny",
        "title", "toe", "toilet", "tomato", "tone", "tongue", "tool", "top", "topic", "total",
        "totally", "touch", "tour", "tourism", "tourist", "toward", "towel", "tower", "toy",
        "track", "trade", "tradition", "traditional", "traffic", "trainer", "training",
        "transfer", "translate", "translation", "transport", "trash", "treat", "treatment",
        "trend", "trick", "trip", "tropical", "true", "trust", "truth", "tube", "tune",
        "tunnel", "turn", "twice", "type", "typical", "ugly", "umbrella", "uncle",
        "uncomfortable", "underground", "underline", "unemployed", "unemployment", "unexpected",
        "unfair", "unfortunately", "unhappy", "uniform", "union", "unit", "united", "universe",
        "unknown", "unless", "unlikely", "unlucky", "unnecessary", "unpleasant", "unusual",
        "update", "upload", "upon", "upper", "upset", "upstairs", "useful", "user", "usual",
        "valley", "valuable", "value", "variety", "various", "vehicle", "version", "victim",
        "victory", "video", "view", "viewer", "violent", "violin", "virus", "visitor",
        "vocabulary", "voice", "volume", "vote", "wage", "waiter", "waitress", "wake", "wall",
        "wallet", "want", "warm", "warn", "warning", "wash", "washing", "waste", "wave",
        "weak", "wealth", "weapon", "wear", "wedding", "week", "weigh", "weight", "west",
        "western", "whale", "whatever", "wheel", "whenever", "whether", "while", "whole",
        "whose", "wide", "widely", "wife", "wild", "wildlife", "willing", "win", "wind",
        "wing", "winner", "wish", "within", "without", "witness", "wood", "wooden", "wool",
        "word", "work", "worker", "working", "worldwide", "worried", "worse", "worst", "worth",
        "would", "wound", "wow", "wrap", "writer", "writing", "written", "yard", "yeah",
        "year", "yes", "yet", "yoga", "yours", "yourself", "youth", "zero", "zone"
    },
    "B1": {
        "abandon", "absolute", "absolutely", "academic", "access", "accommodation", "account",
        "achievement", "act", "action", "actual", "ad", "add", "additional", "admire", "admit",
        "advanced", "affair", "afford", "afterwards", "agency", "agent", "agreement", "aim",
        "alarm", "album", "alcohol", "alcoholic", "alive", "allow", "alter", "alternative",
        "ambition", "ambitious", "amusing", "analysis", "analyze", "ancestor", "animation",
        "anniversary", "announcement", "annoy", "annoyed", "annoying", "annual", "anxiety",
        "anxious", "apology", "appearance", "application", "approach", "appropriate", "approval",
        "approve", "architect", "architecture", "argue", "arrangement", "arrest", "arrival",
        "artificial", "ashamed", "aside", "aspect", "assess", "assessment", "assignment",
        "assist", "assistant", "associate", "associated", "association", "assume", "athlete",
        "atmosphere", "attach", "attack", "attempt", "attend", "attitude", "attract",
        "attraction", "attractive", "automatic", "automatically", "available", "average",
        "aware", "backward", "bacteria", "bake", "balance", "ban", "bank", "bargain", "base",
        "based", "basic", "basically", "basis", "battery", "beat", "beg", "behavior", "belief",
        "bell", "bend", "benefit", "besides", "bet", "beyond", "bill", "bit", "bitter",
        "blame", "blank", "blow", "bold", "bomb", "bond", "border", "bother", "branch",
        "brand", "brave", "breathe", "breathing", "bride", "brief", "broad", "broadcast",
        "budget", "bullet", "bunch", "burn", "bury", "bush", "calm", "campaign", "campus",
        "candidate", "cap", "capable", "capacity", "capture", "care", "career", "careless",
        "case", "cash", "cast", "catch", "category", "cause", "ceiling", "celebration",
        "central", "ceremony", "chain", "challenge", "champion", "championship", "channel",
        "chapter", "charge", "charity", "chart", "chat", "cheat", "cheerful", "chemical",
        "chest", "childhood", "claim", "clause", "clear", "clearly", "click", "client",
        "climate", "close", "closely", "cloth", "clue", "coach", "coal", "coin", "collection",
        "colored", "combine", "comedy", "comfort", "command", "comment", "commercial", "commit",
        "commitment", "committee", "commonly", "communicate", "communication", "community",
        "compare", "comparison", "compete", "competitive", "competitor", "complain", "complex",
        "concentrate", "concentration", "concept", "concern", "concerned", "concerning",
        "concert", "conclude", "conclusion", "condition", "conduct", "conference", "confidence",
        "confident", "confirm", "conflict", "confuse", "confused", "confusing", "connection",
        "conscious", "consequence", "conservative", "considerable", "considerably", "consist",
        "consistent", "constant", "constantly", "construct", "construction", "consume",
        "consumer", "contact", "contain", "container", "contemporary", "content", "contest",
        "context", "continent", "continue", "continuous", "contract", "contrast", "contribute",
        "contribution", "convenient", "convince", "convinced", "cool", "corporate", "council",
        "county", "courage", "course", "court", "cover", "covered", "crash", "creation",
        "creative", "creature", "credit", "crew", "crisis", "criterion", "critic", "critical",
        "criticism", "criticize", "crop", "crucial", "cultural", "cure", "curious", "curly",
        "currency", "current", "currently", "curtain", "curve", "curved", "custom", "cut",
        "cycle", "damage", "damaging", "data", "date", "deal", "dealer", "debate", "debt",
        "decade", "decent", "declare", "decline", "decorate", "decoration", "decrease",
        "deeply", "defeat", "defense", "defend", "define", "definite", "definitely",
        "definition", "delay", "deliberate", "deliberately", "deliver", "delivery", "demand",
        "demonstrate", "dentist", "deny", "depart", "departure", "depend", "dependent",
        "deposit", "depressed", "depressing", "depth", "desert", "deserve", "desire",
        "desperate", "despite", "destination", "destroy", "destruction", "detail", "detailed",
        "detect", "detective", "determine", "determined", "develop", "development", "device",
        "diagram", "dialogue", "diamond", "difficulty", "dig", "direct", "directly", "dirt",
        "disadvantage", "disagree", "disappoint", "disappointed", "disappointing", "disaster",
        "disc", "discipline", "discount", "discovery", "discussion", "dislike", "display",
        "distant", "distinct", "distribute", "distribution", "district", "divide", "division",
        "document", "domestic", "dominate", "donate", "doubt", "dozen", "draft", "drag",
        "dramatic", "dramatically", "drawing", "dressed", "drop", "drug", "drum", "drunk",
        "due", "dull", "dump", "duration", "dynamic", "eager", "earn", "earth", "earthquake",
        "easily", "eastern", "economic", "economy", "edge", "edit", "edition", "editor",
        "educate", "educated", "education", "educational", "effective", "effectively",
        "efficient", "effort", "elderly", "elect", "election", "element", "embarrassed",
        "embarrassing", "emerge", "emotion", "emotional", "emphasis", "emphasize", "employ",
        "employee", "employer", "employment", "enable", "encounter", "encourage", "encouraging",
        "end", "ending", "enemy", "engaged", "engineering", "enhance", "enjoyable", "enormous",
        "enquiry", "ensure", "entertain", "entertaining", "entertainment", "enthusiasm",
        "enthusiastic", "entire", "entirely", "entitle", "entry", "environmental", "episode",
        "equal", "equally", "equipment", "error", "escape", "essay", "essential", "essentially",
        "establish", "estate", "estimate", "ethical", "evaluate", "even", "evil", "examination",
        "examine", "exchange", "excitement", "exhibition", "exist", "existence", "expand",
        "expectation", "expected", "expedition", "expense", "expensive", "experienced",
        "explode", "explore", "explosion", "export", "expose", "express", "expression",
        "extend", "extent", "external", "extraordinary", "extreme", "extremely", "facility",
        "factor", "failure", "fair", "fairly", "faith", "fall", "false", "fame", "familiar",
        "fancy", "far", "fascinating", "fashionable", "fasten", "favor", "fear", "feature",
        "federal", "fee", "feed", "feedback", "feel", "fellow", "female", "fence", "fiction",
        "field", "fighting", "figure", "file", "final", "finance", "financial", "finding",
        "firm", "fit", "fix", "fixed", "flag", "flame", "flash", "flat", "flexible", "float",
        "flood", "flour", "flow", "fold", "folk", "following", "force", "forever", "formal",
        "former", "fortunately", "fortune", "forward", "found", "freedom", "freeze", "frequency",
        "frequently", "friendship", "frighten", "frightening", "frozen", "fry", "fuel",
        "fully", "function", "fund", "fundamental", "funding", "funny", "fur", "further",
        "future", "gain", "gang", "gap", "gas", "gather", "general", "generate", "generous",
        "genre", "gentleman", "ghost", "giant", "glad", "global", "glove", "go", "goods",
        "govern", "grab", "grade", "gradually", "grand", "grant", "grateful", "greatly",
        "greenhouse", "greet", "grocery", "ground", "group", "growth", "guarantee", "guilty",
        "hand", "hang", "happiness", "harbor", "hard", "harm", "harmful", "hatred", "head",
        "health", "healthy", "hearing", "heat", "heating", "heaven", "heel", "hell", "helmet",
        "hence", "herb", "hidden", "highlight", "highly", "hire", "historic", "historical",
        "hit", "hollow", "holy", "honest", "honestly", "honor", "hook", "hope", "hopefully",
        "host", "house", "household", "housing", "humorous", "humor", "hunger", "hunt",
        "hunting", "hurt", "ideal", "identify", "ignore", "illegal", "illness", "illustrate",
        "illustration", "image", "imaginary", "immediate", "immigrant", "impact", "import",
        "importance", "impression", "impressive", "improvement", "inch", "incident", "income",
        "increasingly", "independence", "indicate", "indirect", "individual", "indoor",
        "indoors", "industrial", "infection", "influence", "inform", "informal", "ingredient",
        "initial", "initially", "initiative", "injure", "injured", "inner", "innocent",
        "inquiry", "insect", "inside", "insight", "insist", "inspire", "install", "instance",
        "institute", "institution", "insurance", "intellectual", "intelligence", "intend",
        "intended", "intense", "intention", "interest", "internal", "interpret", "interrupt",
        "investigation", "investment", "invite", "involve", "involved", "iron", "issue",
        "jam", "journal", "judge", "judgment", "justice", "justify", "keen", "key", "kid",
        "killing", "kind", "kiss", "knock", "label", "laboratory", "lack", "layer", "layout",
        "lead", "leadership", "leading", "leak", "lean", "learning", "least", "lecture",
        "legal", "leisure", "length", "level", "library", "license", "lift", "light", "limit",
        "limited", "line", "link", "liquid", "literature", "live", "lively", "living", "load",
        "loan", "local", "locate", "located", "location", "logical", "lonely", "long", "look",
        "loose", "lord", "loss", "lost", "love", "lower", "loyal", "luck", "luxury", "mad",
        "magic", "mainly", "maintain", "majority", "make", "male", "manage", "management",
        "manner", "manufacture", "manufacturing", "mark", "market", "marketing", "marriage",
        "mass", "massive", "master", "match", "matching", "material", "maximum", "means",
        "measurement", "media", "medical", "medicine", "medium", "melt", "mental", "mention",
        "merely", "message", "method", "mild", "military", "mineral", "minimum", "minister",
        "minor", "minority", "mission", "mistake", "mixed", "mixture", "model", "modify",
        "monitor", "moral", "motor", "mount", "mountain", "mouse", "move", "movie", "mud",
        "multiple", "multiply", "murder", "musical", "mysterious", "nail", "narrative",
        "nation", "native", "naturally", "nature", "neat", "necessarily", "need", "needle",
        "negative", "neighborhood", "nerve", "net", "nevertheless", "nightmare", "noise",
        "normal", "northern", "note", "nothing", "notice", "notion", "nuclear", "numerous",
        "nut", "obey", "object", "objective", "obligation", "observation", "observe", "obtain",
        "obvious", "obviously", "occasion", "occasionally", "occur", "odd", "offense", "offend",
        "offensive", "official", "opening", "operate", "operation", "opponent", "opportunity",
        "oppose", "opposed", "opposition", "organ", "organization", "origin", "original",
        "originally", "ought", "outcome", "outer", "outline", "outside", "overall", "owe",
        "own", "pace", "pack", "package", "painful", "pale", "pan", "panel", "pants", "paper",
        "parallel", "parent", "park", "participate", "particular", "particularly", "partly",
        "passage", "passion", "path", "patience", "patient", "payment", "peaceful", "percentage",
        "perfectly", "performance", "perhaps", "permanent", "permission", "permit", "personality",
        "personally", "persuade", "pet", "phase", "phenomenon", "philosophy", "physical",
        "picture", "pile", "pin", "pipe", "pitch", "place", "plain", "plan", "planning",
        "plant", "plastic", "plate", "platform", "play", "pleased", "plot", "plus", "pocket",
        "poem", "poet", "poetry", "point", "pointed", "poison", "poisonous", "policy",
        "polished", "polite", "political", "politician", "politics", "pollution", "pop",
        "popularity", "population", "port", "portrait", "pose", "position", "positive",
        "possess", "possession", "potential", "potentially", "power", "powerful", "practical",
        "practice", "praise", "pray", "prayer", "predict", "prediction", "preference",
        "pregnant", "preparation", "presence", "present", "presentation", "preserve", "press",
        "pressure", "pretend", "pretty", "previous", "previously", "price", "priest", "primary",
        "prime", "prince", "princess", "principle", "print", "printing", "priority", "prison",
        "prisoner", "privacy", "private", "probable", "probably", "procedure", "process",
        "produce", "producer", "production", "profession", "professional", "profit", "program",
        "promote", "promotion", "proof", "proper", "properly", "property", "proposal",
        "propose", "prospect", "protection", "protest", "proud", "prove", "provide",
        "psychological", "psychologist", "psychology", "public", "publication", "publicity",
        "publish", "publishing", "pull", "punish", "punishment", "purchase", "pure", "purely",
        "purpose", "pursue", "push", "qualification", "qualified", "qualify", "quality",
        "quantity", "quarter", "queen", "question", "queue", "quit", "quotation", "quote",
        "race", "racing", "radical", "range", "rank", "rapid", "rapidly", "rare", "rarely",
        "rate", "rather", "raw", "reach", "react", "reaction", "realistic", "reality",
        "realize", "reasonable", "reasonably", "recall", "receipt", "receive", "recent",
        "recently", "reception", "reckon", "recognition", "recognize", "recommend",
        "recommendation", "record", "recording", "recover", "recovery", "reduction", "refer",
        "reference", "reflect", "reform", "refuse", "regard", "region", "regional", "register",
        "regret", "regulation", "reject", "relate", "related", "relation", "relationship",
        "relative", "relatively", "release", "relevant", "relief", "relieve", "religion",
        "religious", "rely", "remain", "remark", "remarkable", "remember", "remind", "remote",
        "removal", "remove", "rent", "repair", "repeat", "repeated", "replace", "reply",
        "report", "represent", "representative", "reputation", "request", "require",
        "requirement", "rescue", "research", "researcher", "reservation", "reserve", "resident",
        "resist", "resolve", "resort", "resource", "respect", "respond", "response",
        "responsibility", "responsible", "rest", "result", "retain", "retire", "retired",
        "retirement", "return", "reveal", "review", "revise", "revolution", "reward", "rhythm",
        "rice", "rid", "ride", "right", "ring", "rise", "risk", "rob", "rock", "role",
        "romantic", "root", "rope", "rough", "roughly", "round", "route", "routine", "row",
        "royal", "rub", "rubber", "rubbish", "rude", "ruin", "rule", "run", "rural", "rush",
        "sad", "sadly", "safe", "safety", "sail", "sailing", "sailor", "salary", "sale",
        "salt", "sample", "sand", "satisfaction", "satisfy", "satisfying", "save", "saving",
        "scale", "scandal", "scare", "scared", "scary", "scene", "schedule", "scheme",
        "school", "science", "scientific", "scientist", "score", "scream", "screen", "script",
        "sculpture", "sea", "seal", "search", "season", "seat", "second", "secondary",
        "secret", "secretary", "section", "sector", "secure", "security", "seed", "seek",
        "seem", "select", "selection", "self", "sell", "senior", "sense", "sensible",
        "sensitive", "sentence", "separate", "sequence", "series", "serious", "seriously",
        "servant", "serve", "service", "session", "set", "setting", "settle", "several",
        "severe", "sex", "sexual", "shade", "shadow", "shake", "shall", "shallow", "shame",
        "shape", "shaped", "share", "sharp", "she", "sheet", "shelf", "shell", "shelter",
        "shift", "shine", "shiny", "ship", "shock", "shocked", "shocking", "shoot", "shooting",
        "shop", "shopping", "short", "shortly", "shot", "shoulder", "shout", "show", "shut",
        "shy", "sick", "side", "sight", "sign", "signal", "significant", "significantly",
        "silence", "silent", "silk", "silly", "silver", "similar", "similarity", "similarly",
        "simple", "simply", "since", "sincere", "sing", "singer", "singing", "single", "sink",
        "sir", "site", "situation", "size", "ski", "skiing", "skill", "skilled", "skin",
        "skirt", "sky", "slave", "sleep", "sleeve", "slice", "slide", "slight", "slightly",
        "slip", "slope", "slow", "slowly", "small", "smart", "smash", "smell", "smile",
        "smoke", "smoking", "smooth", "snake", "snow", "so", "soap", "social", "society",
        "soft", "software", "soil", "solar", "soldier", "solid", "solution", "solve", "somehow",
        "something", "sometimes", "somewhat", "somewhere", "son", "song", "soon", "sore",
        "sorry", "sort", "soul", "sound", "soup", "source", "south", "southern", "space",
        "speak", "speaker", "special", "specialist", "species", "specific", "specifically",
        "speech", "speed", "spell", "spelling", "spend", "spending", "spicy", "spin", "spirit",
        "spiritual", "split", "spoil", "spoken", "sport", "spot", "spread", "spring", "square",
        "stable", "stadium", "staff", "stage", "stair", "stamp", "stand", "standard", "star",
        "stare", "start", "state", "statement", "station", "statistic", "statue", "status",
        "stay", "steady", "steal", "steam", "steel", "steep", "step", "stick", "sticky",
        "stiff", "still", "stock", "stomach", "stone", "stop", "store", "storm", "story",
        "straight", "strange", "stranger", "strategy", "stream", "street", "strength", "stress",
        "stretch", "strict", "strike", "string", "strong", "strongly", "structure", "struggle",
        "student", "studio", "study", "stuff", "stupid", "style", "subject", "submit",
        "substance", "succeed", "success", "successful", "successfully", "such", "sudden",
        "suddenly", "suffer", "sugar", "suggest", "suggestion", "suit", "suitable", "sum",
        "summarize", "summary", "summer", "sun", "supply", "support", "supporter", "suppose",
        "sure", "surely", "surface", "surgery", "surprise", "surprised", "surprising",
        "surround", "surrounding", "survey", "survive", "suspect", "swear", "sweep", "sweet",
        "swim", "swimming", "switch", "symbol", "sympathy", "symptom", "system", "table",
        "tablet", "tail", "take", "tale", "talent", "talented", "talk", "tall", "tank",
        "tap", "tape", "target", "task", "taste", "tax", "tea", "teach", "teacher", "teaching",
        "team", "tear", "technical", "technique", "technology", "teenage", "teenager",
        "telephone", "television", "tell", "temperature", "temporary", "tend", "tendency",
        "tennis", "tension", "tent", "term", "terrible", "terribly", "test", "text", "thank",
        "thanks", "theater", "theme", "themselves", "theory", "therapy", "therefore", "thick",
        "thief", "thin", "thing", "think", "thinking", "thirsty", "though", "thought", "threat",
        "threaten", "throat", "through", "throughout", "throw", "thumb", "thus", "ticket",
        "tidy", "tie", "tight", "till", "time", "tin", "tiny", "tip", "tired", "title",
        "today", "toe", "together", "toilet", "tomorrow", "tone", "tongue", "tonight", "tool",
        "top", "topic", "total", "totally", "touch", "tough", "tour", "tourism", "tourist",
        "toward", "towel", "tower", "town", "toy", "track", "trade", "tradition", "traditional",
        "traffic", "train", "trainer", "training", "transfer", "transform", "transition",
        "translate", "translation", "transport", "travel", "traveler", "treat", "treatment",
        "tree", "trend", "trial", "trick", "trip", "tropical", "trouble", "truck", "true",
        "truly", "trust", "truth", "try", "tube", "tune", "tunnel", "turn", "twin", "type",
        "typical", "typically", "tire", "ugly", "ultimately", "umbrella", "unable", "uncle",
        "uncomfortable", "unconscious", "under", "underground", "understand", "understanding",
        "underwear", "unemployed", "unemployment", "unexpected", "unfair", "unfortunate",
        "unfortunately", "unhappy", "uniform", "union", "unique", "unit", "united", "universe",
        "university", "unknown", "unless", "unlike", "unlikely", "unnecessary", "unpleasant",
        "until", "unusual", "update", "upon", "upper", "upset", "upstairs", "urban", "urge",
        "use", "used", "useful", "user", "usual", "usually", "vacation", "valley", "valuable",
        "value", "van", "variety", "various", "vary", "vast", "vegetable", "vehicle", "venue",
        "version", "very", "via", "victim", "victory", "video", "view", "viewer", "village",
        "violence", "violent", "virtual", "virus", "vision", "visit", "visitor", "vital",
        "vitamin", "voice", "volume", "voluntary", "volunteer", "vote", "wage", "wait",
        "waiter", "wake", "walk", "wall", "want", "war", "warm", "warn", "warning", "wash",
        "washing", "waste", "watch", "water", "wave", "way", "weak", "weakness", "wealth",
        "wealthy", "weapon", "wear", "weather", "web", "website", "wedding", "week", "weekend",
        "weigh", "weight", "welcome", "well", "west", "western", "wet", "whatever", "wheel",
        "whenever", "whereas", "wherever", "whether", "while", "whisper", "whole", "whom",
        "whose", "wide", "widely", "wife", "wild", "wildlife", "willing", "win", "wind",
        "window", "wine", "wing", "winner", "winter", "wire", "wise", "wish", "within",
        "without", "witness", "woman", "wonder", "wonderful", "wood", "wooden", "wool",
        "word", "work", "worker", "working", "world", "worldwide", "worried", "worry",
        "worse", "worst", "worth", "would", "wound", "wrap", "write", "writer", "writing",
        "written", "wrong", "yard", "yeah", "year", "yellow", "yesterday", "yet", "young",
        "youth", "zero", "zone"
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
    """Sabit A1 / A2 / B1 / B2 / C1 / C2 kümelerinden milisaniyede kelime yakalar."""
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
    grup_seviyeleri = {
        "C1_C2": ("C2", "C1"),
        "B1_B2": ("B2", "B1"),
        "A1_A2": ("A2", "A1")
    }
    for sev in grup_seviyeleri.get(grup, ()):
        k, s = havuzdan_kelime_bul(cumle, sev)
        if k:
            return k, s
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