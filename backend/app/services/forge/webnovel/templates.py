"""Subgenre templates: the machinery of each Korean-webnovel subgenre as defaults.

Each template fills a ``WebnovelStyleProfile`` with the progression axis, tier
ladder, reward types, world hooks and arc shape that readers of that subgenre
expect. Templates are *defaults*: the author's Story Charter and directives
override any field, and ``detect.detect_profile`` picks the template from the
source fingerprint when the author gives no genre at all.

All content here is genre convention (public, generic), never source content.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.schemas.webnovel import ChapterShape, GenreEngine, NarrationConventions, ReaderExperience, WebnovelStyleProfile

# Keyword cues (lowercase) -> subgenre. Order matters: more specific first.
SUBGENRE_CUES: List[tuple] = [
    ("regression", ("regress", "regression", "went back in time", "second chance", "returned to the past", "before it all went wrong", "回归", "회귀")),
    ("villainess_transmigration", ("villainess", "transmigrat", "possessed the villain", "reincarnated as the villain", "otome", "reverse harem", "duke's daughter", "악녀")),
    ("tower_climb", ("tower", "floor", "climber", "trial of the", "ascend the", "탑")),
    ("hunter_gate", ("hunter", "gate", "awakened", "awakening", "s-rank", "a-rank", "guild", "raid", "monster surge", "헌터", "게이트")),
    ("dungeon", ("dungeon", "boss room", "loot", "explorer", "던전")),
    ("system_apocalypse", ("system", "status window", "quest", "tutorial", "constellation", "apocalypse", "the day the world", "status", "시스템")),
    ("game_litrpg", ("vr", "virtual reality", "mmorpg", "game world", "npc", "level up", "litrpg", "logged in")),
    ("martial_arts_murim", ("murim", "martial", "sect", "sword saint", "qi", "inner energy", "wuxia", "무림")),
    ("cultivation", ("cultivat", "dao", "immortal", "heavenly tribulation", "spirit stone", "pill", "xianxia", "선협")),
    ("academy", ("academy", "student council", "entrance exam", "freshman", "class a", "professor", "아카데미")),
    ("reincarnated_noble", ("noble", "count", "duke", "marquis", "empire", "heir", "baron", "estate", "court", "귀족")),
    ("entertainment_industry", ("idol", "actor", "audition", "debut", "agency", "drama set", "streamer", "broadcast", "연예")),
    ("sports", ("league", "match", "coach", "striker", "tournament final", "draft pick", "baseball", "football", "basketball", "esports")),
    ("office_life", ("office", "team leader", "department", "chaebol", "corporate", "intern", "직장")),
    ("historical_transmigration", ("joseon", "dynasty", "crown prince", "royal court", "concubine", "scholar-official", "조선")),
    ("apocalypse_survival", ("zombie", "outbreak", "survivor", "shelter", "the end of the world", "wasteland")),
    ("isekai_return", ("returnee", "came back from another world", "returned from the other world", "summoned", "귀환")),
    ("romance_fantasy", ("romance fantasy", "rofan", "contract marriage", "empress", "grand duke", "로판")),
    ("modern_fantasy", ("modern fantasy", "seoul", "urban", "hidden world", "현대 판타지", "현판")),
]

_BASE_NARRATION = NarrationConventions()
_BASE_CHAPTER = ChapterShape()


def _profile(subgenre: str, *, engine: GenreEngine, reader: ReaderExperience, register: str, perspective: str = "first_person", narration: Optional[NarrationConventions] = None, chapter: Optional[ChapterShape] = None, signature: Optional[List[str]] = None) -> WebnovelStyleProfile:
    p = WebnovelStyleProfile(narrator_register=register, perspective=perspective, narration=narration or _BASE_NARRATION.model_copy(deep=True), engine=engine, reader=reader, chapter=chapter or _BASE_CHAPTER.model_copy(deep=True))
    p.engine.subgenre = subgenre
    if signature:
        p.signature_moves = signature + p.signature_moves
    return p


def _windows(enabled: bool = True, density: str = "regular") -> NarrationConventions:
    n = _BASE_NARRATION.model_copy(deep=True)
    n.windows_enabled = enabled
    n.sfx_density = density
    return n


SUBGENRE_TEMPLATES: Dict[str, WebnovelStyleProfile] = {
    "regression": _profile(
        "regression", register="cold_calculating",
        engine=GenreEngine(
            progression_axis="influence and power rebuilt faster than the first life, measured against a remembered timeline",
            tier_ladder=["nobody", "noticed", "recruited", "indispensable", "feared", "kingmaker"],
            reward_types=["foresight cash-in", "face-slap of a first-life betrayer", "pre-empting a disaster everyone else walks into", "recruiting a future legend while they are still a nobody", "quiet vindication nobody else can see"],
            face_slap_cadence="regular",
            knowledge_advantage="Memory of the first life: exact dates, prices, betrayals, hidden talents. It decays as the timeline diverges; the protagonist must decide what to spend it on.",
            world_hooks=["a countdown to a remembered catastrophe", "people the protagonist knows are secretly dangerous or secretly gifted", "auctions/exams/appointments whose outcomes they remember", "the moment the timeline first diverges"],
            typical_arc_shape="remembered event approaches → protagonist positions quietly → others underestimate → event lands differently than the first life → public reversal → the timeline changes and one remembered advantage is spent",
            genre_vocabulary=["the first life", "the previous timeline", "regressor", "divergence", "the future I remember"],
        ),
        reader=ReaderExperience(core_fantasy="Knowing what everyone else does not, and finally being early instead of late.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["cold satisfaction", "dread of divergence", "private grief for the first life", "vindication"], comedy_level="dry", romance_mode="slow_burn_subplot"),
        signature=["a remembered fact stated flatly a beat before it comes true", "the protagonist grieves a person who has not yet betrayed them"],
    ),
    "hunter_gate": _profile(
        "hunter_gate", register="deadpan_pragmatic",
        narration=_windows(True, "regular"),
        engine=GenreEngine(
            progression_axis="Hunter rank and combat capability, verified by measurement crystals, guild ratings and gate clears",
            tier_ladder=["F", "E", "D", "C", "B", "A", "S", "SS", "SSS"],
            reward_types=["measured rank jump on the page", "hidden-talent reveal in front of a guild", "a skill that does more than its description", "clearing a gate above rank", "a legendary hunter recognising the protagonist", "loot / skill gain"],
            face_slap_cadence="regular",
            knowledge_advantage="A unique skill or system nobody else has, with rules and a cost; strength is verifiable and therefore public.",
            world_hooks=["gates opening on a schedule", "guild recruitment and politics", "association rankings", "dungeon breaks", "a hunter licensing exam", "monster surges on the news"],
            typical_arc_shape="new gate/threat → underestimated entry → a fight that reveals one rule of the skill → measured result → recruitment offers / jealousy → a bigger gate opens",
            genre_vocabulary=["Awakened", "Hunter", "Gate", "Rank", "Skill", "Mana", "Association", "Guild", "Raid", "Boss", "Break"],
        ),
        reader=ReaderExperience(core_fantasy="Power that can be measured, growing faster than anyone expects, in a world that has to acknowledge it.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["awe", "adrenaline", "smug calm", "dread"], comedy_level="dry", romance_mode="slow_burn_subplot", violence_level="high"),
        signature=["a status window shown, then the protagonist's dry one-line reaction to it", "a rank reading that stuns the room"],
    ),
    "tower_climb": _profile(
        "tower_climb", register="grim_survivor",
        narration=_windows(True, "regular"),
        engine=GenreEngine(
            progression_axis="Tower floor and trial ranking; each floor is a rule-set to break",
            tier_ladder=["Floor 1-10 (Tutorial)", "Floor 11-30", "Floor 31-60", "Floor 61-90", "Upper Floors", "the Peak"],
            reward_types=["solving a floor's rule in a way the administrators did not expect", "reward selection screen", "a sponsor/constellation taking interest", "saving a party member everyone wrote off", "leaderboard jump"],
            face_slap_cadence="every_arc",
            knowledge_advantage="Reads rules as puzzles; sees the loophole in the trial text.",
            world_hooks=["floor trials with stated rules", "sponsors watching", "rival climbers and their sponsors", "the administrators' hidden agenda", "a floor nobody has cleared"],
            typical_arc_shape="floor rules announced → party assumes the obvious strategy → protagonist reads the loophole → cost paid → clear + reward screen → a sponsor's message reframes everything",
            genre_vocabulary=["Floor", "Trial", "Administrator", "Sponsor", "Climber", "Reward", "Ranking", "Constellation"],
        ),
        reader=ReaderExperience(core_fantasy="Outthinking a rigged game while everyone else plays it straight.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["tension", "cleverness paying off", "grief", "grim humor"], comedy_level="dry", romance_mode="found_family", violence_level="high"),
        signature=["the trial text quoted, then the one word in it the protagonist fixates on"],
    ),
    "system_apocalypse": _profile(
        "system_apocalypse", register="dry_cynical",
        narration=_windows(True, "regular"),
        engine=GenreEngine(
            progression_axis="Level, stats and skills granted by a System that arrived with the end of the world",
            tier_ladder=["Lv.1-10", "Lv.11-30", "Lv.31-60", "Lv.61-99", "Transcendent"],
            reward_types=["level-up window after a hard-won fight", "a quest completed in an unintended way", "a skill evolving", "saving a shelter that laughed", "a constellation's sponsorship message"],
            face_slap_cadence="regular",
            knowledge_advantage="Prior knowledge of the System (regression, foreknowledge, or a unique starting condition) and the discipline to spend it.",
            world_hooks=["scenario announcements", "shelters and their politics", "constellations watching", "hidden quests", "boss appearances on a timer"],
            typical_arc_shape="scenario announced → panic around the protagonist → they act on hidden knowledge → cost → clear → rewards + a new scenario with worse rules",
            genre_vocabulary=["System", "Scenario", "Quest", "Constellation", "Status", "Skill", "Stat", "Shelter", "Incarnation"],
        ),
        reader=ReaderExperience(core_fantasy="Competence at the end of the world; being the one person who read the manual.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["dread", "gallows humor", "fierce protectiveness", "vindication"], comedy_level="regular", romance_mode="slow_burn_subplot", violence_level="high"),
    ),
    "dungeon": _profile(
        "dungeon", register="deadpan_pragmatic", narration=_windows(True, "regular"),
        engine=GenreEngine(progression_axis="Dungeon depth cleared and gear/skill quality", tier_ladder=["Novice", "Explorer", "Veteran", "Elite", "Legend"], reward_types=["loot reveal", "boss mechanic solved", "hidden room", "party recognition"], face_slap_cadence="regular", knowledge_advantage="Unique skill or perfect map memory.", world_hooks=["dungeon floors", "auction house", "guild ranking", "boss timers"], typical_arc_shape="new floor → wrong strategy by others → protagonist's edge → boss → loot + new depth", genre_vocabulary=["Dungeon", "Floor", "Boss", "Loot", "Party", "Guild"]),
        reader=ReaderExperience(core_fantasy="Every descent pays out.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["adrenaline", "greed satisfied", "camaraderie"], comedy_level="dry", violence_level="high"),
    ),
    "villainess_transmigration": _profile(
        "villainess_transmigration", register="sardonic_noble",
        engine=GenreEngine(
            progression_axis="Social capital, safety margin from the scripted death, and the loyalty of people the original story wasted",
            tier_ladder=["condemned", "tolerated", "useful", "protected", "untouchable", "the one who rewrote the story"],
            reward_types=["a scripted humiliation turned into a public win", "a doomed character saved by one changed decision", "the male lead's script breaking", "a rumour reversed in a ballroom", "money made from knowing the plot"],
            face_slap_cadence="regular",
            knowledge_advantage="Knows the novel's plot and everyone's secrets; the plot fights back when she deviates.",
            world_hooks=["balls, teas and audiences with rules", "the original heroine's timeline", "an engagement contract", "the imperial court", "a death flag with a date"],
            typical_arc_shape="a scripted scene approaches → she prepares a deviation → society expects the villainess → she does the unexpected → flag removed, a new flag raised by the deviation itself",
            genre_vocabulary=["the original story", "the heroine", "death flag", "the script", "Your Grace", "Lady", "Duke", "Crown Prince"],
        ),
        reader=ReaderExperience(core_fantasy="Being underestimated in a gilded cage and dismantling it with wit.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["wry amusement", "dread of the script", "warmth from unexpected loyalty", "vindication"], comedy_level="regular", romance_mode="central", violence_level="low"),
        signature=["the private one-liner after a courtier's compliment", "quoting the original novel's line and then breaking it"],
    ),
    "romance_fantasy": _profile(
        "romance_fantasy", register="warm_wry", perspective="third_close_alternating",
        engine=GenreEngine(progression_axis="Standing, safety and the relationship's trust ledger", tier_ladder=["stranger", "contract partner", "ally", "confidant", "beloved"], reward_types=["a slight repaid publicly", "a small unnoticed kindness noticed", "the lead's mask slipping", "a contract clause used as a weapon"], face_slap_cadence="occasional", knowledge_advantage="Reads people and contracts; sometimes foreknowledge.", world_hooks=["imperial politics", "a contract marriage", "seasons and balls", "a rival house"], typical_arc_shape="social trap → private strategy → public scene → reversal → relationship shifts one notch", genre_vocabulary=["Your Grace", "Grand Duke", "Empress", "estate", "the season"]),
        reader=ReaderExperience(core_fantasy="Being chosen by someone who sees clearly, while winning the room.", dopamine_per_chapter=1, reward_gap_max_chapters=3, emotional_palette=["warmth", "tension", "wry amusement", "longing"], comedy_level="regular", romance_mode="central", violence_level="low", interiority_share_target=0.3),
    ),
    "academy": _profile(
        "academy", register="deadpan_pragmatic",
        engine=GenreEngine(progression_axis="Class ranking, practical exam results and faction standing", tier_ladder=["Class F", "Class E", "Class D", "Class C", "Class B", "Class A", "Special Class"], reward_types=["exam result that stuns the professors", "a duel won by rules-lawyering", "a hidden talent revealed before the class", "a mentor's grudging respect", "a rival humbled"], face_slap_cadence="regular", knowledge_advantage="Superior fundamentals or hidden lineage/skill; sometimes foreknowledge of the academy's plot.", world_hooks=["entrance exam", "midterms and practicals", "club/faction recruitment", "a tournament", "the academy's secret"], typical_arc_shape="assessment announced → underestimation → training montage compressed to one scene → the exam → public reversal → faction interest and a new rival", genre_vocabulary=["Class", "Professor", "practical", "duel", "student council", "senior", "junior"]),
        reader=ReaderExperience(core_fantasy="Being the one everyone got wrong.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["vindication", "camaraderie", "amusement", "tension"], comedy_level="regular", romance_mode="slow_burn_subplot"),
    ),
    "martial_arts_murim": _profile(
        "martial_arts_murim", register="cold_calculating", perspective="third_limited",
        engine=GenreEngine(progression_axis="Martial realm and technique mastery", tier_ladder=["Third-rate", "Second-rate", "First-rate", "Peak", "Transcendent", "Heavenly"], reward_types=["a technique understood mid-fight", "a master's identity revealed", "a sect humbled", "a duel won in one exchange", "recognition by a legend"], face_slap_cadence="regular", knowledge_advantage="A lost art, a regressed master's memory, or perfect comprehension.", world_hooks=["sect politics", "the Murim Alliance", "a tournament", "a demonic cult", "a bounty"], typical_arc_shape="insult → restraint → escalation → a duel → the one exchange → the sect's reaction → a greater enemy notices", genre_vocabulary=["Murim", "sect", "qi", "inner energy", "technique", "realm", "elder", "young master", "senior"]),
        reader=ReaderExperience(core_fantasy="Restraint, then an overwhelming answer.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["cold satisfaction", "honor", "awe"], comedy_level="dry", violence_level="high"),
    ),
    "cultivation": _profile(
        "cultivation", register="cold_calculating", perspective="third_limited",
        engine=GenreEngine(progression_axis="Cultivation stage and dao comprehension", tier_ladder=["Qi Refining", "Foundation Establishment", "Core Formation", "Nascent Soul", "Deity Transformation", "Ascension"], reward_types=["breakthrough on the page", "a treasure nobody recognised", "a senior's arrogance punished", "a sect competition won", "a heavenly tribulation survived"], face_slap_cadence="regular", knowledge_advantage="A heaven-defying technique, past-life memory or unique constitution.", world_hooks=["sect competitions", "secret realms", "auctions", "heavenly tribulations", "a demonic path"], typical_arc_shape="resource crisis → gamble → secret realm/competition → breakthrough → arrogant enemy crushed → a bigger world revealed", genre_vocabulary=["cultivation", "dao", "spirit stone", "pill", "sect", "senior brother", "junior sister", "elder", "tribulation"]),
        reader=ReaderExperience(core_fantasy="Rising against heaven one stage at a time.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["awe", "cold satisfaction", "determination"], comedy_level="dry", violence_level="high"),
    ),
    "reincarnated_noble": _profile(
        "reincarnated_noble", register="sardonic_noble",
        engine=GenreEngine(progression_axis="Wealth, territory, influence at court", tier_ladder=["disgraced heir", "solvent", "respected", "indispensable", "power behind the throne"], reward_types=["a debt turned into leverage", "a ledger proving a crime", "an estate turned profitable in one season", "a courtier out-talked", "a rival house exposed"], face_slap_cadence="regular", knowledge_advantage="Modern knowledge (finance, engineering, logistics) or foreknowledge.", world_hooks=["court sessions", "harvests and taxes", "a war on the border", "a marriage market", "a royal audit"], typical_arc_shape="crisis of money/standing → an unglamorous plan → mockery → execution → public results → the court reprices the protagonist", genre_vocabulary=["estate", "ledger", "Count", "Duke", "His Majesty", "the crown", "the treasury"]),
        reader=ReaderExperience(core_fantasy="Winning with competence in a world that only respects birth.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["vindication", "dry amusement", "warmth toward loyal staff"], comedy_level="dry", romance_mode="slow_burn_subplot", violence_level="moderate"),
    ),
    "game_litrpg": _profile(
        "game_litrpg", register="manic_comic", narration=_windows(True, "regular"),
        engine=GenreEngine(progression_axis="Level, class evolution, and in-game fame/wealth", tier_ladder=["Lv.1-50", "Lv.51-100", "Lv.101-200", "Lv.201-300", "Legend"], reward_types=["hidden class unlocked", "exploit discovered", "broadcast viewers exploding", "a raid boss soloed", "an NPC's hidden quest"], face_slap_cadence="regular", knowledge_advantage="Encyclopedic game knowledge or a bug-like skill.", world_hooks=["patches and events", "guild wars", "streaming rankings", "the auction house", "a hidden quest chain"], typical_arc_shape="patch/event → everyone farms the obvious → protagonist finds the exploit → chaos → rewards + notoriety", genre_vocabulary=["Level", "Class", "Quest", "Skill", "Stat", "NPC", "raid", "guild", "patch"]),
        reader=ReaderExperience(core_fantasy="Breaking the game everyone else is grinding.", dopamine_per_chapter=2, reward_gap_max_chapters=1, emotional_palette=["glee", "smugness", "awe"], comedy_level="high", violence_level="moderate"),
    ),
    "office_life": _profile(
        "office_life", register="dry_cynical",
        engine=GenreEngine(progression_axis="Position, reputation and the people who owe the protagonist", tier_ladder=["intern", "associate", "team leader", "department head", "director", "the one the chairman calls"], reward_types=["a presentation that silences the room", "a sabotaged project rescued", "a boss's mistake exposed politely", "a client won", "a promotion nobody expected"], face_slap_cadence="regular", knowledge_advantage="Regression memory of the company's future, or an uncanny skill.", world_hooks=["quarterly reviews", "a merger", "a corrupt executive", "a rival team", "the chairman's succession"], typical_arc_shape="assignment nobody wants → protagonist takes it → colleagues bet on failure → results → the org chart moves", genre_vocabulary=["Team Leader", "Department Head", "Director", "Chairman", "the board", "Senior", "Junior"]),
        reader=ReaderExperience(core_fantasy="Competence finally being priced correctly.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["vindication", "dry amusement", "quiet loyalty"], comedy_level="regular", romance_mode="slow_burn_subplot", violence_level="low"),
    ),
    "entertainment_industry": _profile(
        "entertainment_industry", register="warm_wry",
        engine=GenreEngine(progression_axis="Fame, skill and the industry's respect", tier_ladder=["nobody", "rookie", "rising", "star", "legend"], reward_types=["an audition that stops the room", "a viral clip", "a veteran's recognition", "a sabotage reversed on air", "ratings/records broken"], face_slap_cadence="regular", knowledge_advantage="Regressed star's experience or a system for talent.", world_hooks=["auditions", "award shows", "live broadcasts", "agency politics", "a scandal"], typical_arc_shape="chance → underestimation → performance → reaction shots → industry reprices the protagonist", genre_vocabulary=["debut", "agency", "producer", "PD", "senior", "hoobae", "broadcast"]),
        reader=ReaderExperience(core_fantasy="Talent recognised in front of everyone who doubted it.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["exhilaration", "warmth", "vindication"], comedy_level="regular", romance_mode="slow_burn_subplot", violence_level="low"),
    ),
    "sports": _profile(
        "sports", register="earnest_underdog",
        engine=GenreEngine(progression_axis="Skill ratings, league standing, contracts", tier_ladder=["reserve", "starter", "key player", "star", "legend"], reward_types=["a play nobody saw coming", "a scout's notebook", "a rival forced to acknowledge", "a comeback"], face_slap_cadence="regular", knowledge_advantage="Regression or a system that measures growth.", world_hooks=["matches", "transfer windows", "tournaments", "injuries", "team politics"], typical_arc_shape="match announced → doubts → training beat → the match → the decisive play → standings shift", genre_vocabulary=["coach", "captain", "match", "league", "scout"]),
        reader=ReaderExperience(core_fantasy="Being the difference on the field.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["adrenaline", "camaraderie", "pride"], comedy_level="dry", violence_level="low"),
    ),
    "historical_transmigration": _profile(
        "historical_transmigration", register="sardonic_noble", perspective="third_limited",
        engine=GenreEngine(progression_axis="Standing at court and control over the kingdom's course", tier_ladder=["powerless", "noticed", "trusted", "indispensable", "the hand behind the throne"], reward_types=["a court debate won with modern knowledge", "a famine averted", "a conspiracy exposed", "a minister humbled"], face_slap_cadence="regular", knowledge_advantage="Modern knowledge and history.", world_hooks=["court sessions", "royal exams", "invasions", "succession", "factions"], typical_arc_shape="crisis → unorthodox plan → court mocks → results → factions realign", genre_vocabulary=["Your Majesty", "minister", "the court", "the palace", "scholar"]),
        reader=ReaderExperience(core_fantasy="Rewriting history from inside it.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["vindication", "gravity", "dry amusement"], comedy_level="dry", violence_level="moderate"),
    ),
    "apocalypse_survival": _profile(
        "apocalypse_survival", register="grim_survivor",
        engine=GenreEngine(progression_axis="Territory, supplies, people and the protagonist's own capability", tier_ladder=["alone", "a shelter", "a community", "a faction", "the one others come to"], reward_types=["a supply run that pays off", "a trap sprung on raiders", "a doubter saved and humbled", "a defended wall"], face_slap_cadence="occasional", knowledge_advantage="Foreknowledge or preparedness.", world_hooks=["raids", "weather", "other factions", "the source of the collapse"], typical_arc_shape="threat → preparation → doubters → attack → hold → a new threat", genre_vocabulary=["shelter", "supplies", "raiders", "the outbreak"]),
        reader=ReaderExperience(core_fantasy="Being the one who prepared.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["dread", "grim satisfaction", "protectiveness"], comedy_level="dry", violence_level="high"),
    ),
    "isekai_return": _profile(
        "isekai_return", register="deadpan_pragmatic", narration=_windows(True, "light"),
        engine=GenreEngine(progression_axis="Recovering and applying other-world power in the modern world", tier_ladder=["hidden", "suspected", "confirmed", "national asset", "beyond measure"], reward_types=["a hidden power shown to the wrong person", "a bureaucrat stunned", "a modern problem solved with other-world means", "an old comrade found"], face_slap_cadence="regular", knowledge_advantage="Decades of other-world experience nobody here can see.", world_hooks=["gates appearing", "agencies", "old enemies following", "family life"], typical_arc_shape="modern life → incident → restraint → the power slips → reactions → the agency knocks", genre_vocabulary=["returnee", "the other world", "Awakened", "agency"]),
        reader=ReaderExperience(core_fantasy="Being vastly more than anyone assumes.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["deadpan amusement", "weariness", "warmth"], comedy_level="regular", violence_level="moderate"),
    ),
    "modern_fantasy": _profile(
        "modern_fantasy", register="dry_cynical",
        engine=GenreEngine(progression_axis="Capability and standing in a hidden or emerging supernatural order", tier_ladder=["mundane", "Awakened", "recognised", "elite", "apex"], reward_types=["a hidden power revealed", "an institution forced to notice", "a rival's scheme reversed"], face_slap_cadence="regular", knowledge_advantage="Unique ability or foreknowledge.", world_hooks=["agencies", "clans", "incidents on the news", "an auction"], typical_arc_shape="incident → investigation → confrontation → reveal → institutions react", genre_vocabulary=["Awakened", "ability", "agency", "clan"]),
        reader=ReaderExperience(core_fantasy="A secret advantage in a familiar city.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["dry amusement", "tension", "vindication"], comedy_level="dry", violence_level="moderate"),
    ),
}

SUBGENRE_TEMPLATES["custom"] = _profile(
    "custom", register="dry_cynical",
    engine=GenreEngine(progression_axis="", tier_ladder=[], reward_types=["public reversal of an underestimation", "a deduction landing", "a status gain", "a verbal win", "a small earned reward"], face_slap_cadence="regular", knowledge_advantage="", world_hooks=[], typical_arc_shape="setup → underestimation → escalating test → public reversal → new tier → new threat", genre_vocabulary=[]),
    reader=ReaderExperience(core_fantasy="Competence recognised.", dopamine_per_chapter=1, reward_gap_max_chapters=2, emotional_palette=["vindication", "tension", "dry amusement"], comedy_level="dry"),
)

SUBGENRE_LABELS: Dict[str, str] = {
    "regression": "Regression / second chance", "system_apocalypse": "System apocalypse", "hunter_gate": "Hunter / Gate", "tower_climb": "Tower climb", "dungeon": "Dungeon",
    "villainess_transmigration": "Villainess transmigration", "academy": "Academy", "martial_arts_murim": "Murim / martial arts", "cultivation": "Cultivation (xianxia-style)",
    "reincarnated_noble": "Reincarnated noble / estate builder", "modern_fantasy": "Modern fantasy", "game_litrpg": "Game / LitRPG", "office_life": "Office life / corporate",
    "romance_fantasy": "Romance fantasy (rofan)", "isekai_return": "Returnee", "apocalypse_survival": "Apocalypse survival", "sports": "Sports", "entertainment_industry": "Entertainment industry",
    "historical_transmigration": "Historical transmigration", "custom": "Custom / let the system decide",
}

PLATFORM_NOTES: Dict[str, str] = {
    "novelpia": "Novelpia front page: very short paragraphs, dense inner speech in 'single quotes', frequent one-line punches, a hook in the final line of every episode, comedy allowed even in dark stories.",
    "munpia": "Munpia: slightly longer episodes, male-lead progression emphasis, measured power growth, respectful of genre vocabulary, strong chapter-end reversals.",
    "kakaopage": "KakaoPage: polished, romance-friendly, clear emotional beats, cliffhangers timed to daily release, cinematic scene entries.",
    "naver_series": "Naver Series: broad-audience clarity, strong reader-reward cadence, clean line-by-line readability on mobile.",
    "royalroad": "RoyalRoad: English-native LitRPG/progression conventions; slightly longer paragraphs acceptable; status windows welcome; still ends on hooks.",
    "generic": "Serialized webnovel conventions without a specific platform.",
}


def template_for(subgenre: Optional[str]) -> WebnovelStyleProfile:
    key = (subgenre or "custom").strip().lower()
    return (SUBGENRE_TEMPLATES.get(key) or SUBGENRE_TEMPLATES["custom"]).model_copy(deep=True)


def guess_subgenre(*texts: str) -> Optional[str]:
    """Keyword-cue guess from any free text (brief, genre field, tags, source summaries). None when nothing fires."""
    blob = " ".join(t for t in texts if t).lower()
    if not blob.strip():
        return None
    best: Optional[str] = None
    best_hits = 0
    for name, cues in SUBGENRE_CUES:
        hits = sum(blob.count(c) for c in cues)
        if hits > best_hits:
            best, best_hits = name, hits
    return best if best_hits else None


__all__ = ["PLATFORM_NOTES", "SUBGENRE_CUES", "SUBGENRE_LABELS", "SUBGENRE_TEMPLATES", "guess_subgenre", "template_for"]
