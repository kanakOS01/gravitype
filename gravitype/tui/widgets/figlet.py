"""
Figlet generator to render small-sized ASCII text banners using box-drawing characters.
"""

from typing import List

LETTERS = {
    "a": [
        "┏┓",
        "┣┫",
        "╹╹",
    ],
    "b": [
        "┏┓",
        "┣┫",
        "┗┛",
    ],
    "c": [
        "┏╸",
        "┃ ",
        "┗╸",
    ],
    "d": [
        "┏┓",
        "┃┃",
        "┗┛",
    ],
    "e": [
        "┏╸",
        "┣╸",
        "┗╸",
    ],
    "f": [
        "┏╸",
        "┣╸",
        "╹ ",
    ],
    "g": [
        "┏╸",
        "┃┓",
        "┗┛",
    ],
    "h": [
        "╻╻",
        "┣┫",
        "╹╹",
    ],
    "i": [
        "╻",
        "┃",
        "╹",
    ],
    "j": [
        "╺┓",
        " ┃",
        "┗┛",
    ],
    "k": [
        "╻┏╸",
        "┃┫ ",
        "╹┗╸",
    ],
    "l": [
        "╻ ",
        "┃ ",
        "┗╸",
    ],
    "m": [
        "┏┳┓",
        "┃┃┃",
        "╹ ╹",
    ],
    "n": [
        "┏┓",
        "┃┃",
        "╹╹",
    ],
    "o": [
        "┏┓",
        "┃┃",
        "┗┛",
    ],
    "p": [
        "┏┓",
        "┣┛",
        "╹ ",
    ],
    "q": [
        "┏┓",
        "┃┃",
        "┗┻",
    ],
    "r": [
        "┏┓",
        "┣┫",
        "╹┗",
    ],
    "s": [
        "┏╸",
        "┗┓",
        "╺┛",
    ],
    "t": [
        "╺┳╸",
        " ┃ ",
        " ╹ ",
    ],
    "u": [
        "╻╻",
        "┃┃",
        "┗┛",
    ],
    "v": [
        "┓┏",
        "┃┃",
        "┗┛",
    ],
    "w": [
        "╻ ╻",
        "┃┃┃",
        "┗┻┛",
    ],
    "x": [
        "╺┓┏╸",
        " ┃┃ ",
        "╺┛┗╸",
    ],
    "y": [
        "╻╻",
        "┗┫",
        " ┛",
    ],
    "z": [
        "┏┓",
        "┏┛",
        "┗┛",
    ],
    " ": [
        "  ",
        "  ",
        "  ",
    ],
}

FigletType = List[str]


def combine_figlets(figlets: List[FigletType]) -> str:
    res = []
    for line in range(3):
        temp = ""
        for figlet in figlets:
            temp += figlet[line]
        res.append(temp)
    return "\n".join(res)


def generate_figlet(phrase: str) -> str:
    phrase = phrase.lower()
    figlets = []
    for letter in phrase:
        if letter in LETTERS:
            figlets.append(LETTERS[letter])
        else:
            figlets.append([" ", " ", " "])
    return combine_figlets(figlets)
