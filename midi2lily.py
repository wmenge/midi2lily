import math
from fractions import Fraction
#import mido

# Helper class that can convert a position/length fraction
# into a number of bars and beats indicating a position in a song
#class Position

# Every piece of Lilypond information is contained in an expression
# { }
class Expression:

    def __init__(self):
        self.children = []

    def get_clef(self):
        if self.lowest_pitch() < 55 and self.highest_pitch() < 67:
            return 'bass'

    def get_length(self):
        length = 0

        for expression in self.children:
            if isinstance(expression, Note):
                length += expression.duration.fraction
            elif isinstance(expression, Expression):
                length += expression.getLength()
        
        return length

    def get_pitches(self):
        pitches = []
        for expression in self.children:
            if isinstance(expression, Note):
                pitches.append(expression.pitch)
            if isinstance(expression, Chord):
                pitches.extend(expression.pitches)
            elif isinstance(expression, Expression):
                pitches.extend(expression.get_pitches())
        return pitches

    def lowest_pitch(self):
        pitches = self.get_pitches()
        if len(pitches) == 0:
            return 108
        return min(pitch.pitch for pitch in pitches)

    def highest_pitch(self):
        pitches = self.get_pitches()
        if len(pitches) == 0:
            return 0
        return max(pitch.pitch for pitch in pitches)

    # break out into length/position class
    def format_length(fraction):
        return "m {}, b {}".format((fraction.numerator // fraction.denominator), (fraction.numerator % fraction.denominator))

    def formatted_length(self):
        return format_length(self.get_length)

    def __str__(self):
        result = "{\n"

        if self.get_clef() != None:
            result += "\clef {}\n".format(self.get_clef())

        for expression in self.children:
            result += str(expression) + "\n"
        result += "}"
        return result

# Container for multiple voices. Expected to be similar in length
class PolyphonicContext:

    def __init__(self):
        self.children = []

    def __str__(self):
        return "<<\n"+ '\n\\\\\n'.join(map(str, self.children)) + ">>"

# A staff is a command followed by an expression that is contained in the staff
class Staff(Expression):

    def __init__(self, name = "new staff"):
        self.name = name
        super().__init__()

    def __str__(self):
        return "\\new Staff = \"{}\" ".format(self.name) + super().__str__()

# Groups a number of staves. A simple song is expected to have one staff group
class StaffGroup(Expression):

    def __str__(self):
        return "\\new StaffGroup <<\n{}\n>>".format("\n".join(map(str, self.children)))

# Note, Rest, Chord should be immutable
class Rest:

    def __init__(self, duration):
        self.duration = duration

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.duration == other.duration

    def __hash__(self):
        return hash(self.duration)

    def __str__(self):
        assert(isinstance(self.duration, Duration))
        # bad hack: compound durations are represented as:
        # "1~ 4" where the second note implicitly gets the same pitch
        # as the previous. For rests this does not work
        return 'r' + str(self.duration).replace('~ ', ' r')
        
class Note:

    def __init__(self, pitch, duration):
        self.pitch = pitch
        self.duration = duration

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitch == other.pitch and self.duration == other.duration

    def __hash__(self):
        return hash(tuple(self.pitch)) + hash(self.duration)

    def __str__(self):
        assert(isinstance(self.duration, Duration))
        return str(self.pitch) + str(self.duration)

class Chord:

    def __init__(self, pitches, duration):
        self.pitches = pitches # should be a set
        self.duration = duration

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitches == other.pitches and self.duration == other.duration

    def __hash__(self):
        return hash(tuple(self.pitches)) + hash(self.duration)

    def __str__(self):
        assert(isinstance(self.duration, Duration))
        return str("<{}>".format(' '.join(map(str, self.pitches)))) + str(self.duration)

# Converts a midi note number in a note name
# TODO: enharmonics, respect key signature
class Pitch:

    # todo: flats
    noteNames = [ 'c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b' ]

    def __init__(self, pitch):
        self.pitch = pitch

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitch == other.pitch
        
    def __hash__(self):
        return hash(self.pitch)

    def __str__(self):
        # 21 = a0, 12 notes in an octave
        # pitch 60 is a C' (, and ' denote octaves, suchs A0 a,, and C3 c'''
        octave = (self.pitch // 12) - 4
        sign = "'" if (octave > 0) else ","
        octaveString = sign * abs(octave)
        return self.noteNames[self.pitch % 12] + octaveString

# A duration measured as a fraction
class Duration:

    def get_duration(ticks, ticks_per_beat, denominator):
        beatFraction = Fraction(ticks, ticks_per_beat)
        return Duration(Fraction(beatFraction.numerator, beatFraction.denominator * denominator))

    def __init__(self, fraction):
        self.fraction = fraction

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.fraction == other.fraction
    
    def __hash__(self):
        return hash(self.fraction)

    def can_be_expresses_as_simple_note(self):
        return self.fraction.numerator == 1

    def can_be_expresses_as_dotted_note(self):
        return (self.fraction.denominator > 1) and (((self.fraction.numerator + 1) % 4) == 0)

    def __str__(self):

        if (self.can_be_expresses_as_simple_note()):
            # simple duration
            return str(self.fraction.denominator)
        elif (self.can_be_expresses_as_dotted_note()):
            # dotted duration
            wholeNote = Fraction((self.fraction.numerator + 1)//2, self.fraction.denominator)
            numberOfDots = int(math.log(self.fraction.numerator + 1,2)-1)
            return str(wholeNote.denominator) + "." * numberOfDots
        else:
            # bruteforce the biggest whole duration we can find
            i = 1
            while i < self.fraction.numerator:
                wholeNote = Fraction(self.fraction.numerator - i, self.fraction.denominator)
                if wholeNote.numerator == 1:
                    remainder = Duration(self.fraction - wholeNote)
                    return str(wholeNote.denominator) + "~ " + str(remainder)
                i += 1

            return "should not happen"

# Can a file have multiple expressions, or just a single one?
class File:

    def __init__(self, version="2.19.48"):
        self.expressions = []
        self.version = version

    def __str__(self):
        result = "\\version \"{}\"".format(self.version)

        if (self.expressions != []):
            result += "\n\n"
            for expression in self.expressions:
                result += str(expression)

        return result

class TimeSignature:

    def __init__(self, ticks_per_beat, fraction):
        self.ticks_per_beat = ticks_per_beat
        self.fraction = fraction

class BuildContext:

    def __init__(self):
        self.staff = None
        self.previous_note = None
        self.currentNote = None
        self.time_signature = None

#    def position(self):

def is_note_on_message(msg):
    return msg.type == 'note_on' and msg.velocity > 0

def is_note_off_message(msg):
    return msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)

def note_on_handler(msg, staff, ticks_per_beat, denominator):

    if (msg.time > 0):
        # indicates a rest
        rest = Rest(Duration.get_duration(msg.time, ticks_per_beat, denominator))
        staff.children.append(rest)
        return rest

    if (msg.time == 0):
        # inidicates start of a normal note
        note = Note(Pitch(msg.note), Duration.get_duration(msg.time, ticks_per_beat, denominator))
        return note

# check if we can omit previous notee and work from staff instead
# check if we can call staff expression
def note_off_handler(msg, staff, ticks_per_beat, denominator, previous_note):

    if (msg.time > 0):
        # indicates a new note
        note = Note(Pitch(msg.note), Duration.get_duration(msg.time, ticks_per_beat, denominator))
        staff.children.append(note)
        return note
    
    elif (msg.time == 0):
        staff.children.pop()

        # indicates part of a chord
        if isinstance(previous_note, Note):
            chord = Chord([previous_note.pitch, Pitch(msg.note)], previous_note.duration)
        if isinstance(previous_note, Chord):
            previous_note.pitches.append(Pitch(msg.note))
            chord = Chord(previous_note.pitches, previous_note.duration)

        staff.children.append(chord)
        return chord
            
def convert(midifile):

    file = File()
    staffGroup = None

    denominator = None
    staff = None

    for i, track in enumerate(midifile.tracks):

        # state machine
        if (i > 0):

            # ignore control track
            staff = Staff(track.name)
            
            # first track gets added directly to file.
            # a second track causes a staffgroup to be inserted
            if len(file.expressions) == 0:
                file.expressions.append(staff)
            else:
                if staffGroup == None:
                    staffGroup = StaffGroup()
                    staffGroup.children.extend(file.expressions)
                    file.expressions = [staffGroup]
                staffGroup.children.append(staff)

        for msg in track:

            # for now, ignore changes in time signature mid song
            if msg.type == 'time_signature' and denominator == None:
                denominator = msg.denominator

            if is_note_on_message(msg):
                previous_note = note_on_handler(msg, staff, midifile.ticks_per_beat, denominator) #, staff, midifile.ticks_per_beat, denominator)
                
            if is_note_off_message(msg):
                previous_note = note_off_handler(msg, staff, midifile.ticks_per_beat, denominator, previous_note)

    return file