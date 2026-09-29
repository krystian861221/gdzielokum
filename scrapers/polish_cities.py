import re
from typing import Optional

def normalize_slug(text: str) -> str:
    """Konwertuje tekst z polskimi znakami na bezpieczny slug url, np. 'Jelenia Góra' -> 'jelenia-gora'."""
    text = text.lower().strip()
    replacements = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
        'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
    }
    for pol, lat in replacements.items():
        text = text.replace(pol, lat)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

# Baza ścieżek Otodom dla miast i powiatów
OTODOM_PATHS = {
    # Dolnośląskie
    "wroclaw": "dolnoslaskie/wroclaw/wroclaw/wroclaw",
    "jelenia-gora": "dolnoslaskie/jelenia-gora/jelenia-gora/jelenia-gora",
    "legnica": "dolnoslaskie/legnica/legnica/legnica",
    "walbrzych": "dolnoslaskie/walbrzych/walbrzych/walbrzych",
    "lubin": "dolnoslaskie/lubin/lubin/lubin",
    "swidnica": "dolnoslaskie/swidnica/swidnica/swidnica",
    "boleslawiec": "dolnoslaskie/boleslawiec/boleslawiec/boleslawiec",
    "olesnica": "dolnoslaskie/olesnica/olesnica/olesnica",
    "dzierzoniow": "dolnoslaskie/dzierzoniow/dzierzoniow/dzierzoniow",
    "glagow": "dolnoslaskie/glogow/glogow/glogow",
    "glogow": "dolnoslaskie/glogow/glogow/glogow",
    "klodzko": "dolnoslaskie/klodzko/klodzko/klodzko",
    "jawor": "dolnoslaskie/jawor/jawor/jawor",
    "luban": "dolnoslaskie/luban/luban/luban",
    "zgorzelec": "dolnoslaskie/zgorzelec/zgorzelec/zgorzelec",
    "kamienna-gora": "dolnoslaskie/kamienna-gora/kamienna-gora/kamienna-gora",
    "piechowice": "dolnoslaskie/jelenie-gora/piechowice",
    "kowary": "dolnoslaskie/jelenie-gora/kowary",
    "karpacz": "dolnoslaskie/jelenie-gora/karpacz",
    "szklarska-poreba": "dolnoslaskie/jelenie-gora/szklarska-poreba",
    "stankowice": "dolnoslaskie/lubanski/lesna/stankowice",
    "lesna": "dolnoslaskie/lubanski/lesna",
    "gryfow-slaski": "dolnoslaskie/lwowecki/gryfow-slaski",
    "lwowek-slaski": "dolnoslaskie/lwowecki/lwowek-slaski",

    # Mazowieckie
    "warszawa": "mazowieckie/warszawa/warszawa/warszawa",
    "radom": "mazowieckie/radom/radom/radom",
    "plock": "mazowieckie/plock/plock/plock",
    "siedlce": "mazowieckie/siedlce/siedlce/siedlce",
    "pruszkow": "mazowieckie/pruszkow/pruszkow/pruszkow",
    "legionowo": "mazowieckie/legionowo/legionowo/legionowo",
    "ostroleka": "mazowieckie/ostroleka/ostroleka/ostroleka",
    "piaseczno": "mazowieckie/piaseczno/piaseczno/piaseczno",
    "otwock": "mazowieckie/otwock/otwock/otwock",

    # Małopolskie
    "krakow": "malopolskie/krakow/krakow/krakow",
    "tarnow": "malopolskie/tarnow/tarnow/tarnow",
    "nowy-sacz": "malopolskie/nowy-sacz/nowy-sacz/nowy-sacz",
    "oswiecim": "malopolskie/oswiecim/oswiecim/oswiecim",
    "zakopane": "malopolskie/tatrzanski/zakopane",
    "wieliczka": "malopolskie/wielicki/wieliczka",

    # Wielkopolskie
    "poznan": "wielkopolskie/poznan/poznan/poznan",
    "kalisz": "wielkopolskie/kalisz/kalisz/kalisz",
    "konin": "wielkopolskie/konin/konin/konin",
    "pila": "wielkopolskie/pila/pila/pila",
    "ostrow-wielkopolski": "wielkopolskie/ostrow-wielkopolski/ostrow-wielkopolski/ostrow-wielkopolski",
    "gniezno": "wielkopolskie/gniezno/gniezno/gniezno",
    "leszno": "wielkopolskie/leszno/leszno/leszno",

    # Pomorskie
    "gdansk": "pomorskie/gdansk/gdansk/gdansk",
    "gdynia": "pomorskie/gdynia/gdynia/gdynia",
    "sopot": "pomorskie/sopot/sopot/sopot",
    "slupsk": "pomorskie/slupsk/slupsk/slupsk",
    "tczew": "pomorskie/tczew/tczew/tczew",
    "wejherowo": "pomorskie/wejherowo/wejherowo/wejherowo",

    # Śląskie
    "katowice": "slaskie/katowice/katowice/katowice",
    "czestochowa": "slaskie/czestochowa/czestochowa/czestochowa",
    "sosnowiec": "slaskie/sosnowiec/sosnowiec/sosnowiec",
    "gliwice": "slaskie/gliwice/gliwice/gliwice",
    "zabrze": "slaskie/zabrze/zabrze/zabrze",
    "bielsko-biala": "slaskie/bielsko-biala/bielsko-biala/bielsko-biala",
    "bytom": "slaskie/bytom/bytom/bytom",
    "ruda-slaska": "slaskie/ruda-slaska/ruda-slaska/ruda-slaska",
    "rybnik": "slaskie/rybnik/rybnik/rybnik",
    "tychy": "slaskie/tychy/tychy/tychy",
    "dabrowa-gornicza": "slaskie/dabrowa-gornicza/dabrowa-gornicza/dabrowa-gornicza",
    "chorzow": "slaskie/chorzow/chorzow/chorzow",

    # Łódzkie
    "lodz": "lodzkie/lodz/lodz/lodz",
    "piotrkow-trybunalski": "lodzkie/piotrkow-trybunalski/piotrkow-trybunalski/piotrkow-trybunalski",
    "pabianice": "lodzkie/pabianice/pabianice/pabianice",
    "tomaszow-mazowiecki": "lodzkie/tomaszow-mazowiecki/tomaszow-mazowiecki/tomaszow-mazowiecki",
    "belchatow": "lodzkie/belchatow/belchatow/belchatow",
    "zgierz": "lodzkie/zgierz/zgierz/zgierz",

    # Zachodniopomorskie
    "szczecin": "zachodniopomorskie/szczecin/szczecin/szczecin",
    "koszalin": "zachodniopomorskie/koszalin/koszalin/koszalin",
    "stargard": "zachodniopomorskie/stargard/stargard/stargard",
    "kolobrzeg": "zachodniopomorskie/kolobrzeg/kolobrzeg/kolobrzeg",
    "swinoujscie": "zachodniopomorskie/swinoujscie/swinoujscie/swinoujscie",

    # Kujawsko-Pomorskie
    "bydgoszcz": "kujawsko-pomorskie/bydgoszcz/bydgoszcz/bydgoszcz",
    "torun": "kujawsko-pomorskie/torun/torun/torun",
    "wloclawek": "kujawsko-pomorskie/wloclawek/wloclawek/wloclawek",
    "grudziadz": "kujawsko-pomorskie/grudziadz/grudziadz/grudziadz",
    "inowroclaw": "kujawsko-pomorskie/inowroclaw/inowroclaw/inowroclaw",

    # Lubelskie
    "lublin": "lubelskie/lublin/lublin/lublin",
    "zamosc": "lubelskie/zamosc/zamosc/zamosc",
    "chelm": "lubelskie/chelm/chelm/chelm",
    "biala-podlaska": "lubelskie/biala-podlaska/biala-podlaska/biala-podlaska",
    "pulawy": "lubelskie/pulawy/pulawy/pulawy",

    # Podkarpackie
    "rzeszow": "podkarpackie/rzeszow/rzeszow/rzeszow",
    "przemysl": "podkarpackie/przemysl/przemysl/przemysl",
    "stalowa-wola": "podkarpackie/stalowa-wola/stalowa-wola/stalowa-wola",
    "mielec": "podkarpackie/mielec/mielec/mielec",
    "tarnobrzeg": "podkarpackie/tarnobrzeg/tarnobrzeg/tarnobrzeg",
    "krosno": "podkarpackie/krosno/krosno/krosno",

    # Podlaskie
    "bialystok": "podlaskie/bialystok/bialystok/bialystok",
    "suwalki": "podlaskie/suwalki/suwalki/suwalki",
    "lomza": "podlaskie/lomza/lomza/lomza",

    # Świętokrzyskie
    "kielce": "swietokrzyskie/kielce/kielce/kielce",
    "ostrowiec-swietokrzyski": "swietokrzyskie/ostrowiec-swietokrzyski/ostrowiec-swietokrzyski/ostrowiec-swietokrzyski",
    "starachowice": "swietokrzyskie/starachowice/starachowice/starachowice",
    "skarDetails": "swietokrzyskie/skarzysko-kamienna/skarzysko-kamienna/skarzysko-kamienna",

    # Lubuskie
    "zielona-gora": "lubuskie/zielona-gora/zielona-gora/zielona-gora",
    "gorzow-wielkopolski": "lubuskie/gorzow-wielkopolski/gorzow-wielkopolski/gorzow-wielkopolski",
    "nowa-sol": "lubuskie/nowa-sol/nowa-sol/nowa-sol",
    "zary": "lubuskie/zary/zary/zary",

    # Warmińsko-Mazurskie
    "olsztyn": "warminsko-mazurskie/olsztyn/olsztyn/olsztyn",
    "elblag": "warminsko-mazurskie/elblag/elblag/elblag",
    "elk": "warminsko-mazurskie/elk/elk/elk",

    # Opolskie
    "opole": "opolskie/opole/opole/opole",
    "kedzierzyn-kozle": "opolskie/kedzierzyn-kozle/kedzierzyn-kozle/kedzierzyn-kozle",
    "nysa": "opolskie/nysa/nysa/nysa",
    "brzeg": "opolskie/brzeg/brzeg/brzeg"
}

VOIVODESHIPS = [
    "dolnoslaskie", "mazowieckie", "malopolskie", "wielkopolskie",
    "pomorskie", "slaskie", "lodzkie", "zachodniopomorskie",
    "kujawsko-pomorskie", "lubelskie", "podkarpackie", "podlaskie",
    "swietokrzyskie", "lubuskie", "warminsko-mazurskie", "opolskie"
]

def get_otodom_path(city_name: str) -> str:
    """Zwraca ścieżkę dla Otodom na podstawie wpisanego miasta."""
    slug = normalize_slug(city_name)
    if slug in OTODOM_PATHS:
        return OTODOM_PATHS[slug]
    
    # Przeszukaj częściowe dopasowania
    for key, path in OTODOM_PATHS.items():
        if slug in key or key in slug:
            return path
            
    # Domyślny format: dolnoslaskie/{slug}/{slug}/{slug}
    return f"dolnoslaskie/{slug}/{slug}/{slug}"
