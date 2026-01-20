from api.midi.midi_types import MidiEventType

MIDI_EVENT_TYPES: list[MidiEventType] = [
    "C-1",
    "C#-1",
    "Db-1",
    "D-1",
    "D#-1",
    "Eb-1",
    "E-1",
    "F-1",
    "F#-1",
    "Gb-1",
    "G-1",
    "G#-1",
    "Ab-1",
    "A-1",
    "A#-1",
    "Bb-1",
    "B-1",
    "C0",
    "C#0",
    "Db0",
    "D0",
    "D#0",
    "Eb0",
    "E0",
    "F0",
    "F#0",
    "Gb0",
    "G0",
    "G#0",
    "Ab0",
    "A0",
    "A#0",
    "Bb0",
    "B0",
    "C1",
    "C#1",
    "Db1",
    "D1",
    "D#1",
    "Eb1",
    "E1",
    "F1",
    "F#1",
    "Gb1",
    "G1",
    "G#1",
    "Ab1",
    "A1",
    "A#1",
    "Bb1",
    "B1",
    "C2",
    "C#2",
    "Db2",
    "D2",
    "D#2",
    "Eb2",
    "E2",
    "F2",
    "F#2",
    "Gb2",
    "G2",
    "G#2",
    "Ab2",
    "A2",
    "A#2",
    "Bb2",
    "B2",
    "C3",
    "C#3",
    "Db3",
    "D3",
    "D#3",
    "Eb3",
    "E3",
    "F3",
    "F#3",
    "Gb3",
    "G3",
    "G#3",
    "Ab3",
    "A3",
    "A#3",
    "Bb3",
    "B3",
    "C4",
    "C#4",
    "Db4",
    "D4",
    "D#4",
    "Eb4",
    "E4",
    "F4",
    "F#4",
    "Gb4",
    "G4",
    "G#4",
    "Ab4",
    "A4",
    "A#4",
    "Bb4",
    "B4",
    "C5",
    "C#5",
    "Db5",
    "D5",
    "D#5",
    "Eb5",
    "E5",
    "F5",
    "F#5",
    "Gb5",
    "G5",
    "G#5",
    "Ab5",
    "A5",
    "A#5",
    "Bb5",
    "B5",
    "C6",
    "C#6",
    "Db6",
    "D6",
    "D#6",
    "Eb6",
    "E6",
    "F6",
    "F#6",
    "Gb6",
    "G6",
    "G#6",
    "Ab6",
    "A6",
    "A#6",
    "Bb6",
    "B6",
    "C7",
    "C#7",
    "Db7",
    "D7",
    "D#7",
    "Eb7",
    "E7",
    "F7",
    "F#7",
    "Gb7",
    "G7",
    "G#7",
    "Ab7",
    "A7",
    "A#7",
    "Bb7",
    "B7",
    "C8",
    "C#8",
    "Db8",
    "D8",
    "D#8",
    "Eb8",
    "E8",
    "F8",
    "F#8",
    "Gb8",
    "G8",
    "G#8",
    "Ab8",
    "A8",
    "A#8",
    "Bb8",
    "B8",
    "C9",
    "C#9",
    "Db9",
    "D9",
    "D#9",
    "Eb9",
    "E9",
    "F9",
    "F#9",
    "Gb9",
    "G9",
    # GM drum events
    "acousticbassdrum",
    "lowbassdrum",
    "lobassdrum",
    "electricbassdrum",
    "highbassdrum",
    "hibassdrum",
    "sidestick",
    "acousticsnare",
    "handclap",
    "electricsnare",
    "rimshot",
    "lowfloortom",
    "lofloortom",
    "closedhihat",
    "highfloortom",
    "hifloortom",
    "pedalhihat",
    "lowtom",
    "lotom",
    "openhihat",
    "lowmidtom",
    "lomidtom",
    "highmidtom",
    "himidtom",
    "crashcymbal1",
    "hightom",
    "hitom",
    "ridecymbal1",
    "chinesecymbal",
    "ridebell",
    "tambourine",
    "splashcymbal",
    "cowbell",
    "crashcymbal2",
    "vibraslap",
    "ridecymbal2",
    "highbongo",
    "hibongo",
    "lowbongo",
    "lobongo",
    "mutehighconga",
    "mutehiconga",
    "openhighconga",
    "openhiconga",
    "lowconga",
    "loconga",
    "hightimbale",
    "hitimbale",
    "lowtimbale",
    "lotimbale",
    "highagogo",
    "hiagogo",
    "highagogô",
    "hiagogô",
    "highagog",
    "hiagog",
    "lowagogo",
    "loagogo",
    "lowagogô",
    "loagogô",
    "lowagog",
    "loagog",
    "cabasa",
    "maracas",
    "shortwhistle",
    "longwhistle",
    "shortguiro",
    "shortgüiro",
    "shortgiro",
    "longguiro",
    "longgüiro",
    "longgiro",
    "claves",
    "highwoodblock",
    "hiwoodblock",
    "lowwoodblock",
    "lowoodblock",
    "mutecuica",
    "mutecuíca",
    "opencuica",
    "opencuíca",
    "mutetriangle",
    "opentriangle",
    # CC events
    "modwheel",
    "modulationwheel",
    "sustain",
    "sustainpedal",
    "allnotesoff",
    "allnoteson",
    "allnotesoffon",
    "resetallcontrollers",
]


MIDI_EVENT_TO_HEX: dict[MidiEventType, tuple[int, int]] = {
    "C-1": (0x90, 0),
    "C#-1": (0x90, 1),
    "Db-1": (0x90, 1),  # Same as C#-1
    "D-1": (0x90, 2),
    "D#-1": (0x90, 3),
    "Eb-1": (0x90, 3),  # Same as D#-1
    "E-1": (0x90, 4),
    "F-1": (0x90, 5),
    "F#-1": (0x90, 6),
    "Gb-1": (0x90, 6),  # Same as F#-1
    "G-1": (0x90, 7),
    "G#-1": (0x90, 8),
    "Ab-1": (0x90, 8),  # Same as G#-1
    "A-1": (0x90, 9),
    "A#-1": (0x90, 10),
    "Bb-1": (0x90, 10),  # Same as A#-1
    "B-1": (0x90, 11),
    "C0": (0x90, 12),
    "C#0": (0x90, 13),
    "Db0": (0x90, 13),  # Same as C#0
    "D0": (0x90, 14),
    "D#0": (0x90, 15),
    "Eb0": (0x90, 15),  # Same as D#-1
    "E0": (0x90, 16),
    "F0": (0x90, 17),
    "F#0": (0x90, 18),
    "Gb0": (0x90, 18),  # Same as F#0
    "G0": (0x90, 19),
    "G#0": (0x90, 20),
    "Ab0": (0x90, 20),  # Same as G#0
    "A0": (0x90, 21),
    "A#0": (0x90, 22),
    "Bb0": (0x90, 22),  # Same as A#0
    "B0": (0x90, 23),
    "C1": (0x90, 24),
    "C#1": (0x90, 25),
    "Db1": (0x90, 25),  # Same as C#1
    "D1": (0x90, 26),
    "D#1": (0x90, 27),
    "Eb1": (0x90, 27),  # Same as D#1
    "E1": (0x90, 28),
    "F1": (0x90, 29),
    "F#1": (0x90, 30),
    "Gb1": (0x90, 30),  # Same as F#1
    "G1": (0x90, 31),
    "G#1": (0x90, 32),
    "Ab1": (0x90, 32),  # Same as G#1
    "A1": (0x90, 33),
    "A#1": (0x90, 34),
    "Bb1": (0x90, 34),  # Same as A#1
    "B1": (0x90, 35),
    "C2": (0x90, 36),
    "C#2": (0x90, 37),
    "Db2": (0x90, 37),  # Same as C#2
    "D2": (0x90, 38),
    "D#2": (0x90, 39),
    "Eb2": (0x90, 39),  # Same as D#2
    "E2": (0x90, 40),
    "F2": (0x90, 41),
    "F#2": (0x90, 42),
    "Gb2": (0x90, 42),  # Same as F#2
    "G2": (0x90, 43),
    "G#2": (0x90, 44),
    "Ab2": (0x90, 44),  # Same as G#2
    "A2": (0x90, 45),
    "A#2": (0x90, 46),
    "Bb2": (0x90, 46),  # Same as A#2
    "B2": (0x90, 47),
    "C3": (0x90, 48),
    "C#3": (0x90, 49),
    "Db3": (0x90, 49),  # Same as C#3
    "D3": (0x90, 50),
    "D#3": (0x90, 51),
    "Eb3": (0x90, 51),  # Same as D#3
    "E3": (0x90, 52),
    "F3": (0x90, 53),
    "F#3": (0x90, 54),
    "Gb3": (0x90, 54),  # Same as F#3
    "G3": (0x90, 55),
    "G#3": (0x90, 56),
    "Ab3": (0x90, 56),  # Same as G#3
    "A3": (0x90, 57),
    "A#3": (0x90, 58),
    "Bb3": (0x90, 58),  # Same as A#3
    "B3": (0x90, 59),
    "C4": (0x90, 60),
    "C#4": (0x90, 61),
    "Db4": (0x90, 61),  # Same as C#4
    "D4": (0x90, 62),
    "D#4": (0x90, 63),
    "Eb4": (0x90, 63),  # Same as D#4
    "E4": (0x90, 64),
    "F4": (0x90, 65),
    "F#4": (0x90, 66),
    "Gb4": (0x90, 66),  # Same as F#4
    "G4": (0x90, 67),
    "G#4": (0x90, 68),
    "Ab4": (0x90, 68),  # Same as G#4
    "A4": (0x90, 69),
    "A#4": (0x90, 70),
    "Bb4": (0x90, 70),  # Same as A#4
    "B4": (0x90, 71),
    "C5": (0x90, 72),
    "C#5": (0x90, 73),
    "Db5": (0x90, 73),  # Same as C#5
    "D5": (0x90, 74),
    "D#5": (0x90, 75),
    "Eb5": (0x90, 75),  # Same as D#5
    "E5": (0x90, 76),
    "F5": (0x90, 77),
    "F#5": (0x90, 78),
    "Gb5": (0x90, 78),  # Same as F#5
    "G5": (0x90, 79),
    "G#5": (0x90, 80),
    "Ab5": (0x90, 80),  # Same as G#5
    "A5": (0x90, 81),
    "A#5": (0x90, 82),
    "Bb5": (0x90, 82),  # Same as A#5
    "B5": (0x90, 83),
    "C6": (0x90, 84),
    "C#6": (0x90, 85),
    "Db6": (0x90, 85),  # Same as C#6
    "D6": (0x90, 86),
    "D#6": (0x90, 87),
    "Eb6": (0x90, 87),  # Same as D#6
    "E6": (0x90, 88),
    "F6": (0x90, 89),
    "F#6": (0x90, 90),
    "Gb6": (0x90, 90),  # Same as F#6
    "G6": (0x90, 91),
    "G#6": (0x90, 92),
    "Ab6": (0x90, 92),  # Same as G#6
    "A6": (0x90, 93),
    "A#6": (0x90, 94),
    "Bb6": (0x90, 94),  # Same as A#6
    "B6": (0x90, 95),
    "C7": (0x90, 96),
    "C#7": (0x90, 97),
    "Db7": (0x90, 97),  # Same as C#7
    "D7": (0x90, 98),
    "D#7": (0x90, 99),
    "Eb7": (0x90, 99),  # Same as D#7
    "E7": (0x90, 100),
    "F7": (0x90, 101),
    "F#7": (0x90, 102),
    "Gb7": (0x90, 102),  # Same as F#7
    "G7": (0x90, 103),
    "G#7": (0x90, 104),
    "Ab7": (0x90, 104),  # Same as G#7
    "A7": (0x90, 105),
    "A#7": (0x90, 106),
    "Bb7": (0x90, 106),  # Same as A#7
    "B7": (0x90, 107),
    "C8": (0x90, 108),
    "C#8": (0x90, 109),
    "Db8": (0x90, 109),  # Same as C#8
    "D8": (0x90, 110),
    "D#8": (0x90, 111),
    "Eb8": (0x90, 111),  # Same as D#8
    "E8": (0x90, 112),
    "F8": (0x90, 113),
    "F#8": (0x90, 114),
    "Gb8": (0x90, 114),  # Same as F#8
    "G8": (0x90, 115),
    "G#8": (0x90, 116),
    "Ab8": (0x90, 116),  # Same as G#8
    "A8": (0x90, 117),
    "A#8": (0x90, 118),
    "Bb8": (0x90, 118),  # Same as A#8
    "B8": (0x90, 119),
    "C9": (0x90, 120),
    "C#9": (0x90, 121),
    "Db9": (0x90, 121),  # Same as C#9
    "D9": (0x90, 122),
    "D#9": (0x90, 123),
    "Eb9": (0x90, 123),  # Same as D#9
    "E9": (0x90, 124),
    "F9": (0x90, 125),
    "F#9": (0x90, 126),
    "Gb9": (0x90, 126),  # Same as F#9
    "G9": (0x90, 127),
    # GM drum events
    "acousticbassdrum": (0x90, 35),  # Acoustic Bass Drum
    "lowbassdrum": (0x90, 35),  # Low Bass Drum
    "lobassdrum": (0x90, 35),  # Low Bass Drum
    "electricbassdrum": (0x90, 36),  # Electric Bass Drum
    "highbassdrum": (0x90, 36),  # High Bass Drum
    "hibassdrum": (0x90, 36),  # High Bass Drum
    "sidestick": (0x90, 37),  # Side Stick
    "acousticsnare": (0x90, 38),  # Acoustic Snare
    "handclap": (0x90, 39),  # Hand Clap
    "electricsnare": (0x90, 40),  # Electric Snare
    "rimshot": (0x90, 40),  # Rimshot
    "lowfloortom": (0x90, 41),  # Low Floor Tom
    "lofloortom": (0x90, 41),  # Low Floor Tom
    "closedhihat": (0x90, 42),  # Closed Hi-hat
    "highfloortom": (0x90, 43),  # High Floor Tom
    "hifloortom": (0x90, 43),  # High Floor Tom
    "pedalhihat": (0x90, 44),  # Pedal Hi-hat
    "lowtom": (0x90, 45),  # Low Tom
    "lotom": (0x90, 45),  # Low Tom
    "openhihat": (0x90, 46),  # Open Hi-hat
    "lowmidtom": (0x90, 47),  # Low-Mid Tom
    "lomidtom": (0x90, 47),  # Low-Mid Tom
    "highmidtom": (0x90, 48),  # High-Mid Tom
    "himidtom": (0x90, 48),  # High-Mid Tom
    "crashcymbal1": (0x90, 49),  # Crash Cymbal 1
    "hightom": (0x90, 50),  # High Tom
    "hitom": (0x90, 50),  # High Tom
    "ridecymbal1": (0x90, 51),  # Ride Cymbal 1
    "chinesecymbal": (0x90, 52),  # Chinese Cymbal
    "ridebell": (0x90, 53),  # Ride Bell
    "tambourine": (0x90, 54),  # Tambourine
    "splashcymbal": (0x90, 55),  # Splash Cymbal
    "cowbell": (0x90, 56),  # Cowbell
    "crashcymbal2": (0x90, 57),  # Crash Cymbal 2
    "vibraslap": (0x90, 58),  # Vibraslap
    "ridecymbal2": (0x90, 59),  # Ride Cymbal 2
    "highbongo": (0x90, 60),  # High Bongo
    "hibongo": (0x90, 60),  # High Bongo
    "lowbongo": (0x90, 61),  # Low Bongo
    "lobongo": (0x90, 61),  # Low Bongo
    "mutehighconga": (0x90, 62),  # Mute High Conga
    "mutehiconga": (0x90, 62),  # Mute High Conga
    "openhighconga": (0x90, 63),  # Open High Conga
    "lowconga": (0x90, 64),  # Low Conga
    "loconga": (0x90, 64),  # Low Conga
    "hightimbale": (0x90, 65),  # High Timbale
    "hitimbale": (0x90, 65),  # High Timbale
    "lowtimbale": (0x90, 66),  # Low Timbale
    "lotimbale": (0x90, 66),  # Low Timbale
    "highagogo": (0x90, 67),  # High Agogo
    "hiagogo": (0x90, 67),  # High Agogo
    "highagogô": (0x90, 67),  # High Agogô
    "hiagogô": (0x90, 67),  # High Agogô
    "highagog": (0x90, 67),  # High Agog
    "hiagog": (0x90, 67),  # High Agog
    "lowagogo": (0x90, 68),  # Low Agogo
    "loagogo": (0x90, 68),  # Low Agogo
    "lowagogô": (0x90, 68),  # Low Agogô
    "loagogô": (0x90, 68),  # Low Agogô
    "lowagog": (0x90, 68),  # Low Agog
    "loagog": (0x90, 68),  # Low Agog
    "cabasa": (0x90, 69),  # Cabasa
    "maracas": (0x90, 70),  # Maracas
    "shortwhistle": (0x90, 71),  # Short Whistle
    "longwhistle": (0x90, 72),  # Long Whistle
    "shortguiro": (0x90, 73),  # Short Guiro
    "shortgüiro": (0x90, 73),  # Short Güiro
    "shortgiro": (0x90, 73),  # Short Giro
    "longguiro": (0x90, 74),  # Long Guiro
    "longgüiro": (0x90, 74),  # Long Güiro
    "longgiro": (0x90, 74),  # Long Giro
    "claves": (0x90, 75),  # Claves
    "highwoodblock": (0x90, 76),  # High Woodblock
    "hiwoodblock": (0x90, 76),  # High Woodblock
    "lowwoodblock": (0x90, 77),  # Low Woodblock
    "lowoodblock": (0x90, 77),  # Low Woodblock
    "mutecuica": (0x90, 78),  # Mute Cuica
    "mutecuíca": (0x90, 78),  # Mute Cuíca
    "opencuica": (0x90, 79),  # Open Cuica
    "opencuíca": (0x90, 79),  # Open Cuíca
    "mutetriangle": (0x90, 80),  # Mute Triangle
    "opentriangle": (0x90, 81),  # Open Triangle
    # CC events
    "modwheel": (0xB0, 1),
    "modulationwheel": (0xB0, 1),
    "sustain": (0xB0, 64),
    "sustainpedal": (0xB0, 64),
    "allnotesoff": (0xB0, 123),
    "allnoteson": (0xB0, 123),
    "allnotesoffon": (0xB0, 123),
    "resetallcontrollers": (0xB0, 121),
}
