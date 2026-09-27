"""Word pools.

Two lists ship with the game; players add their own by dropping a ``.txt``
file into ``~/.gravitype/words/`` (or ``$GRAVITYPE_HOME/words/``). The file
stem becomes a category, so ``rust.txt`` gives you a RUST category alongside
TECH and GENERAL.

Entries are taken verbatim - spaces, digits, punctuation and capitals are all
allowed, so a set of phrases works as well as a set of single words. Matching
in the game folds case, so a file written with capitals is still typeable
without reaching for shift.
"""

import random

from gravitype.core.paths import words_dir

#: Word sets that ship with the game. A custom file sharing one of these names
#: is ignored rather than allowed to shadow it.
BUILTIN_CATEGORIES = ("tech", "general")

#: Custom sets are read from files with this suffix.
WORD_FILE_SUFFIX = ".txt"

TECH_WORDS = [
    "python",
    "rust",
    "golang",
    "java",
    "ruby",
    "kotlin",
    "swift",
    "docker",
    "git",
    "nosql",
    "redis",
    "postgres",
    "sqlite",
    "mysql",
    "mongodb",
    "graphql",
    "rest",
    "react",
    "django",
    "fastapi",
    "flask",
    "nextjs",
    "vue",
    "svelte",
    "angular",
    "html",
    "css",
    "json",
    "yaml",
    "xml",
    "markdown",
    "terminal",
    "console",
    "shell",
    "bash",
    "zsh",
    "linux",
    "macos",
    "windows",
    "kernel",
    "thread",
    "process",
    "memory",
    "buffer",
    "cache",
    "stack",
    "heap",
    "pointer",
    "variable",
    "function",
    "method",
    "class",
    "object",
    "module",
    "package",
    "library",
    "framework",
    "compiler",
    "linker",
    "interpreter",
    "debugger",
    "profiler",
    "latency",
    "throughput",
    "bandwidth",
    "network",
    "socket",
    "client",
    "server",
    "api",
    "microservice",
    "monolith",
    "cloud",
    "lambda",
    "kubernetes",
    "ansible",
    "terraform",
    "pipeline",
    "deploy",
    "release",
    "rollback",
    "logging",
    "metric",
    "tracing",
    "monitor",
    "alert",
    "security",
    "exploit",
    "firewall",
    "encryption",
    "decryption",
    "cipher",
    "token",
    "session",
    "cookie",
    "auth",
    "oauth",
    "jwt",
    "hash",
    "checksum",
    "algorithm",
    "sorting",
    "searching",
    "recursion",
    "closure",
    "decorator",
    "generator",
    "iterator",
    "coroutine",
    "asyncio",
    "callback",
    "promise",
    "future",
    "observer",
    "singleton",
    "factory",
]

GENERAL_WORDS = [
    "gravity",
    "keyboard",
    "typing",
    "practice",
    "accuracy",
    "speed",
    "victory",
    "defeat",
    "challenge",
    "champion",
    "master",
    "rookie",
    "expert",
    "legend",
    "galaxy",
    "nebula",
    "cosmos",
    "universe",
    "planet",
    "asteroid",
    "comet",
    "orbit",
    "rocket",
    "shuttle",
    "satellite",
    "eclipse",
    "solstice",
    "equinox",
    "matrix",
    "vortex",
    "portal",
    "tunnel",
    "passage",
    "horizon",
    "zenith",
    "nadir",
    "apex",
    "summit",
    "abyss",
    "canyon",
    "glacier",
    "volcano",
    "tsunami",
    "cyclone",
    "monsoon",
    "breeze",
    "tempest",
    "whisper",
    "thunder",
    "lightning",
    "shadow",
    "reflection",
    "mirage",
    "phantom",
    "specter",
    "vision",
    "dream",
    "illusion",
    "paradox",
    "enigma",
    "riddle",
    "puzzle",
    "mystery",
    "secret",
    "beacon",
    "signal",
    "radar",
    "sonar",
    "compass",
    "anchor",
    "rudder",
    "sails",
    "journey",
    "voyage",
    "odyssey",
    "quest",
    "mission",
    "venture",
    "hazard",
    "danger",
    "safety",
    "shelter",
    "oasis",
    "miracle",
    "wonder",
    "marvel",
    "spark",
    "ember",
    "flame",
    "blaze",
    "torrent",
    "cascade",
    "fountain",
]


#: Populated by refresh(); maps a lowercase set name to its entries.
_custom_sets = {}

#: Files that were found but not used, as {name: reason}. Surfaced on the
#: Help screen so a set that silently failed to load is still visible.
_skipped = {}


def is_typeable(entry: str) -> bool:
    """Whether an entry is something a player could actually type.

    Entries must be printable ASCII. Phrases, punctuation, digits and capitals
    all qualify; accented and non-Latin characters do not, since they cannot be
    typed on a plain keyboard. Requiring ASCII also means a binary file dropped
    in the words directory is rejected rather than loading as a category of
    unmatchable garbage - its bytes decode to non-ASCII replacement characters.
    """
    return bool(entry) and entry.isascii() and entry.isprintable()


def parse_word_file(text: str) -> list:
    """Turn a word file's contents into entries.

    One entry per line. Leading and trailing whitespace is trimmed and blank
    lines are dropped; everything else is kept exactly as written, because a
    custom set is allowed to contain phrases, punctuation and capitals.
    Duplicates are removed, keeping first appearance, so a repeated entry does
    not quietly become twice as likely to spawn. Matching is case-sensitive,
    so ``Rust`` and ``rust`` are different entries and both are kept.
    """
    seen = set()
    entries = []
    for line in text.splitlines():
        entry = line.strip()
        if not is_typeable(entry):
            continue
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
    return entries


def refresh() -> None:
    """Re-scan the words directory.

    Best-effort, like ``Config`` and ``Stats``: an unreadable file or a
    missing directory leaves the built-in sets working rather than raising.
    Called at import and again whenever the menu is shown, so a file added
    mid-session appears without a restart.
    """
    _custom_sets.clear()
    _skipped.clear()

    directory = words_dir()
    try:
        paths = sorted(directory.glob(f"*{WORD_FILE_SUFFIX}"))
    except OSError:
        return

    for path in paths:
        name = path.stem.strip().casefold()

        if not name:
            continue
        if name in BUILTIN_CATEGORIES:
            _skipped[path.name] = "name is reserved by a built-in category"
            continue

        try:
            # errors="replace" so a stray byte costs one character, not the
            # whole file.
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            _skipped[path.name] = "could not be read"
            continue

        entries = parse_word_file(text)
        if not entries:
            # An empty pool would make random.choice() raise at spawn time.
            _skipped[path.name] = "no usable entries"
            continue

        _custom_sets[name] = entries


def custom_sets() -> dict:
    """The loaded custom sets, as {name: entries}."""
    return dict(_custom_sets)


def skipped_files() -> dict:
    """Files found in the words directory that were not loaded."""
    return dict(_skipped)


def available_categories() -> list:
    """Every playable category: the built-ins first, then custom sets."""
    return list(BUILTIN_CATEGORIES) + sorted(_custom_sets)


def word_pool(category: str) -> list:
    """The entries for ``category``, falling back to tech for an unknown one."""
    name = (category or "").strip().casefold()
    if name == "general":
        return GENERAL_WORDS
    if name in _custom_sets:
        return _custom_sets[name]
    return TECH_WORDS


def get_random_word(category: str = "tech", level: int = 1) -> str:
    """
    Get a random word from the specified category.
    Filters words by length based on the current level to increase difficulty:
    - Level 1: 3-5 letters
    - Level 2: 4-7 letters
    - Level 3: 5-9 letters
    - Level 4+: 6+ letters
    """
    pool = word_pool(category)

    # Filter word pool by length corresponding to current level
    if level == 1:
        filtered_pool = [w for w in pool if 3 <= len(w) <= 5]
    elif level == 2:
        filtered_pool = [w for w in pool if 4 <= len(w) <= 7]
    elif level == 3:
        filtered_pool = [w for w in pool if 5 <= len(w) <= 9]
    else:
        filtered_pool = [w for w in pool if len(w) >= 6]

    # Fallback in case the band is empty - a set of phrases has nothing short
    # enough for the early levels, so it draws from the whole pool instead.
    if not filtered_pool:
        filtered_pool = pool

    return random.choice(filtered_pool)


refresh()
