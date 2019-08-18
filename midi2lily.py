import math
from fractions import Fraction
from functools import reduce

# Every piece of Lilypond information is contained in an expression
# { }
# TODO: split into rendering part and parse utility part
class Expression:

    def __init__(self):
        self._children = []
    
    def add(self, child):
        if type(child) is list:
            self._children.extend(child)
        else:
            self._children.append(child)
    
    def pop(self):
        return self._children.pop()
        
    def last(self):
        return self._children[-1]
            
    def get_clef(self):
        if self.lowest_pitch() < 55 and self.highest_pitch() < 67:
            return 'bass'

    def length(self):
        lengths = list(map(lambda x: x.length(), self._children))
        return sum(lengths)
        
    # removes all expressions after position from this expressions
    # returns a new expression that contains all
    def split_at(self, position):
        length = 0
                
        for i, expression in enumerate(self._children):
            length += expression.length()
                
            if length > position:
                expression = Expression()
                expression.add(self._children[i:])
                self._children = self._children[0:i]
                return expression

    def pitches(self):
        pitches = set()
        for expression in self._children:
            if isinstance(expression, Note):
                pitches.add(expression.pitch.pitch)
            if isinstance(expression, Chord):
                pitches.update(pitch.pitch for pitch in expression.pitches)
            elif isinstance(expression, Expression):
                pitches.update(pitch.pitch for pitch in expression.pitches())
        return pitches
        
    def lowest_pitch(self):
        return min(self.pitches(),default=108)
        
    def highest_pitch(self):
        return max(self.pitches(),default=0)

    # break out into length/position class
    def format_length(fraction):
        return "m {}, b {}".format((fraction.numerator // fraction.denominator), (fraction.numerator % fraction.denominator))

    def formatted_length(self):
        return Expression.format_length(self.get_length)

    def __str__(self):
        result = "{\n"

        if self.get_clef() != None:
            result += "\clef {}\n".format(self.get_clef())

        for expression in self._children:
            result += str(expression) + "\n"
        result += "}"
        return result

# Container for multiple voices. Expected to be similar in length
class PolyphonicContext:

    def __init__(self):
        self.__children = []
        
    def add(self, child):
        if type(child) is list:
            self.__children.extend(child)
        else:
            self.__children.append(child)
            
    # TODO: Try to prevent access to voices
    def voices(self):
        return self.__children

    def __str__(self):
        return "<<\n"+ '\n\\\\\n'.join(map(str, sorted(self.__children, key=PolyphonicContext.sort_function, reverse=True))) + "\n>>"

    def length(self):
        lengths = list(map(lambda x: x.length(), self.__children))
        longest = max(lengths, default=0)
        return longest
    
    def sort_function(e):
        # when printing a polyphonic context, sort by average pitch, so that 
        # highest voice is printed first and is drawn with stems up
        pitches = e.pitches()
        return sum(pitches) / len(pitches)

# A staff is a command followed by an expression that is contained in the staff
class Staff(Expression):

    def __init__(self, name="new staff"):
        self.__name = name
        super().__init__()

    def __str__(self):
        return "\\new Staff = \"{}\" ".format(self.__name) + super().__str__()

# Groups a number of staves. A simple song is expected to have one staff group
class StaffGroup(Expression):

    def __str__(self):
        return "\\new StaffGroup <<\n{}\n>>".format("\n".join(map(str, self._children)))

# Note, Rest, Chord should be immutable
class Rest:

    def __init__(self, duration):
        self.duration = duration
    
    # TODO: Generalized super class?    
    def length(self):
        return self.duration.length()

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
    
    def get_from_midi_note(midi_note, context):
        pitch = Pitch(midi_note.pitch)
        duration = Duration.get_duration(midi_note.end - midi_note.start, context.time_signature.ticks_per_beat, context.time_signature.denominator)
        return Note(pitch, duration)

    def __init__(self, pitch, duration):
        # TODO: rename to midinote
        self.pitch = pitch
        self.duration = duration
        
    def length(self):
        return self.duration.length()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitch == other.pitch and self.duration == other.duration

    def __hash__(self):
        return hash(tuple(self.pitch)) + hash(self.duration)

    def __str__(self):
        assert(isinstance(self.duration, Duration))
        return str(self.pitch) + str(self.duration)

# add helper method to create a chord from note + pitch or chord + pitch
class Chord:
    
    def construct_chord(note1, note2):
        
        assert(isinstance(note1, Note) or isinstance(note1, Chord))
        assert(isinstance(note2, Note) or isinstance(note2, Chord))
        assert(note1.duration == note2.duration)
        
        pitches = set()
        
        if isinstance(note1, Note):
            pitches.add(note1.pitch)
        else:
            pitches.update(note1.pitches)
        
        if isinstance(note2, Note):
            pitches.add(note2.pitch)
        else:
            pitches.update(note2.pitches)
        
        return Chord(pitches, note1.duration)
        
    def __init__(self, pitches, duration):
        self.pitches = set(pitches)
        self.duration = duration

    def length(self):
        return self.duration.length()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitches == other.pitches and self.duration == other.duration

    def __hash__(self):
        return hash(tuple(self.pitches)) + hash(self.duration)

    def __str__(self):
        assert(isinstance(self.duration, Duration))
        return str("<{}>".format(' '.join(map(str, sorted(self.pitches))))) + str(self.duration)

# Converts a midi note number in a note name
# TODO: enharmonics, respect key signature
class Pitch:

    # todo: flats
    noteNames = [ 'c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b' ]

    def __init__(self, pitch):
        self.pitch = pitch

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pitch == other.pitch
        
    def __lt__(self, other):
        return isinstance(other, self.__class__) and self.pitch < other.pitch
        
    def __le__(self, other):
        return isinstance(other, self.__class__) and self.pitch <= other.pitch

    def __gt__(self, other):
        return isinstance(other, self.__class__) and self.pitch > other.pitch

    def __ge__(self, other):
        return isinstance(other, self.__class__) and self.pitch >= other.pitch
        
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
# also doubles as position
# TODO: Also store midi time/ticks?
class Position:
    
    def get_position(ticks, ticks_per_beat, denominator):
        beatFraction = Fraction(ticks, ticks_per_beat)
        return Position(Fraction(beatFraction.numerator, beatFraction.denominator * denominator))

    def __init__(self, fraction):
        self._fraction = fraction
    
    # todo: misnomer for position
    def length(self):
        return self._fraction

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.length() == other.length()
        
    def __lt__(self, other):
        return isinstance(other, self.__class__) and self.length() < other.length()
    
    def __le__(self, other):
        return isinstance(other, self.__class__) and self.length() <= other.length()

    def __gt__(self, other):
        return isinstance(other, self.__class__) and self.length() > other.length()

    def __ge__(self, other):
        return isinstance(other, self.__class__) and self.length() >= other.length()
    
    def __hash__(self):
        return hash(self._fraction)

    def __str__(self):
        return str(self._fraction)

class Duration(Position):

    def get_duration(ticks, ticks_per_beat, denominator):
        beatFraction = Fraction(ticks, ticks_per_beat)
        return Duration(Fraction(beatFraction.numerator, beatFraction.denominator * denominator))

    def can_be_expresses_as_simple_note(self):
        return self._fraction.numerator == 1

    def can_be_expresses_as_dotted_note(self):
        return (self._fraction.denominator > 1) and (((self._fraction.numerator + 1) % 4) == 0)
        
    def length(self):
        return self._fraction

    def __str__(self):

        if (self.can_be_expresses_as_simple_note()):
            # simple duration
            return str(self._fraction.denominator)
        elif (self.can_be_expresses_as_dotted_note()):
            # dotted duration
            wholeNote = Fraction((self._fraction.numerator + 1)//2, self._fraction.denominator)
            numberOfDots = int(math.log(self._fraction.numerator + 1,2)-1)
            return str(wholeNote.denominator) + "." * numberOfDots
        else:
            # bruteforce the biggest whole duration we can find
            i = 1
            while i < self._fraction.numerator:
                wholeNote = Fraction(self._fraction.numerator - i, self._fraction.denominator)
                if wholeNote.numerator == 1:
                    remainder = Duration(self._fraction - wholeNote)
                    return str(wholeNote.denominator) + "~ " + str(remainder)
                i += 1

            return "should not happen"

# Can a file have multiple expressions, or just a single one?
class File:

    def __init__(self, version="2.19.48"):
        self.__children = []
        self.__version = version
        
    def add(self, child):
        if type(child) is list:
            self.__children.extend(child)
        else:
            self.__children.append(child)
            
    def pop(self):
        return self.__children.pop()
            
    def empty(self):
        return not self.__children
        
    # TODO: prevent access to __children
    def expressions(self):
        return self.__children

    def __str__(self):
        result = "\\version \"{}\"".format(self.__version)

        if (self.__children != []):
            result += "\n\n"
            for expression in self.__children:
                result += str(expression)

        return result

# TODO: Add midi resolution (ticks per beat)
class TimeSignature:
    
    def __init__(self, numerator, denominator, ticks_per_beat):
        self.numerator = numerator
        self.denominator = denominator
        self.ticks_per_beat = ticks_per_beat
        
    def __str__(self):
        return "\\time {}/{}".format(self.numerator, self.denominator)
        
# a representation of midi note as start, end and pitch  
class MidiNote:
    
    def __init__(self, start, end, pitch):
        self.start = start
        self.end = end
        self.pitch = pitch
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.start == other.start and self.end == other.end and self.pitch == other.pitch
        
    def __hash__(self):
        return hash(str(self.start) + str(self.end) + str(self.pitch))

# TODO: Split into file parse context that does not reset
#       and track parse context that resets for every track   
class ParseContext:

    def __init__(self):
        self.position = 0
        # rename to open expression so it can also hold a polyphonic fragment?
        self.staff = None
        self.polyphonic_context = None
        self.time_signature = None
        self.active_pitches = {}
        self.midi_notes = []

def is_note_on_message(msg):
    return msg.type == 'note_on' and msg.velocity > 0

def is_note_off_message(msg):
    return msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)

def note_on_handler(msg, context):

    # Add pitch to list of active pitches and their start position
    context.active_pitches[msg.note] = context.position

    if (msg.time > 0):
        # indicates a rest
        rest = Rest(Duration.get_duration(msg.time, context.time_signature.ticks_per_beat, context.time_signature.denominator))
        context.staff.add(rest)
        return rest    
    
# check if we can omit previous note and work from staff instead
def note_off_handler(msg, context):
    midi_note = convert_to_midi_note(msg, context)
    handle_midi_note(midi_note, context)
    
def convert_to_midi_note(msg, context):
    
    assert msg.note in context.active_pitches
    
    start_position = context.active_pitches.pop(msg.note)
    duration = context.position - start_position
    
    midi_note = MidiNote(start_position, context.position, msg.note)
    
    return midi_note

def handle_midi_note(midi_note, context):
    
    note = Note.get_from_midi_note(midi_note, context)
    
    start = Position.get_position(midi_note.start, context.time_signature.ticks_per_beat, context.time_signature.denominator)
        
    if fit_note_in_expression(note, start, context.staff): return
            
    # if we have arrived here we will need a polyphonic context
    if context.polyphonic_context == None:
        context.polyphonic_context = PolyphonicContext()
        context.polyphonic_context.add(context.staff.split_at(start.length()))
        context.staff.add(context.polyphonic_context)
    
    # try to fit the note into any of the children of the polyphonic context
    for expression in context.polyphonic_context.voices():
        # recalculate start in terms of expression
        local_start = Position(start.length() - (context.staff.length() - context.polyphonic_context.length()))
        if fit_note_in_expression(note, local_start, expression): return
        
    # if we arrive here the note does not fit in any of the existing voices, create a new one
    expression = Expression()
    context.polyphonic_context.add(expression)

    if fit_note_in_expression(note, Position(0), expression): return
   
# TODO: Add to expression class
def fit_note_in_expression(note, start, expression):
    # check if this note can be added to the score as a simple note (no polyphony, no chord)
    # if gap add rest
    if (start.length() >= expression.length()):
        expression.add(note)
        return True
    
    # check if this note can be added to the score as a chord
    previous_note = expression.last()
    
    # TODO: refactor in can_be_added_to and replace with
    if previous_note != None and (isinstance(previous_note, Note) or isinstance(previous_note, Chord)):
        start_of_previous_note = expression.length() - previous_note.length()
    
        if (start.length() >= start_of_previous_note) and (note.duration == previous_note.duration):
            chord = Chord.construct_chord(note, previous_note)
            expression.pop()
            expression.add(chord)
            return True
      
def convert(midifile):

    file = File()
    staffGroup = None
    context = ParseContext()
    
    for i, track in enumerate(midifile.tracks):
        
        context.position = 0
        context.midi_notes = []

        # ignore control track
        if (i > 0):

            # TODO: track handler function
            context.staff = Staff(track.name)
            
            # first track gets added directly to file.
            # a second track causes a staffgroup to be inserted
            if file.empty():
                file.add(context.staff)
            else:
                if staffGroup == None:
                    staffGroup = StaffGroup()
                    staffGroup.add(file.expressions())
                    file.pop()
                    file.add(staffGroup)
                staffGroup.add(context.staff)

        for msg in track:
            
            context.position += msg.time
            
            # for now, ignore changes in time signature mid song
            if msg.type == 'time_signature' and context.time_signature == None:
                context.time_signature = TimeSignature(msg.numerator, msg.denominator, midifile.ticks_per_beat)

            if is_note_on_message(msg):
                note_on_handler(msg, context)
                
            if is_note_off_message(msg):
                note_off_handler(msg, context)

    return file