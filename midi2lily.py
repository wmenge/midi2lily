import sys
import math
import mido
from fractions import Fraction
from functools import reduce


# TODO Split into File render context and Staff Render context
# TODO Move lots of decision making in __str__ to render context
# TODO Split __str__ in two versions: one for context, one without
class RenderContext:

    def __init__(self):
        self.position = 0
        self.time_signature = TimeSignature(4, 4)
        self.previous_pitch = None
        self.previous_duration = None
        self.relative = True
        self.relative_base = 60

        # bad hack to get relative pitches for chords right. refactor
        self.previous_pitch = None

# Every piece of Lilypond information is an expression
class Expression:
    
    def length(self):
        return 0

class TextExpression(Expression):
    
    def __init__(self, content):
        self.__content = content
        
    def __str__(self):
        return self.__content

# Every expression can be contained in a compound expression
# { }
# TODO: split into rendering part and parse utility part
class CompoundExpression(Expression):

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
        if len(self._children) > 0:
            return self._children[-1]
            
    def get_clef(self):
        if self.lowest_pitch() < 55:
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
                expression = CompoundExpression()
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
            elif isinstance(expression, CompoundExpression):
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

    def merge(self, other):
        assert(isinstance(other, CompoundExpression))
        self._children.extend(other._children)

    def __str__(self, context = None):

        result = ""

        if isinstance(context, RenderContext) and context.relative:
            context.relative_base = 60
            context.previous_pitch = None
            result += str(TextExpression("\\relative {} ".format(str(Pitch(context.relative_base)))))
        
        result += "{\n"

        if self.get_clef() != None:
            result += "\clef {}\n".format(self.get_clef())
            

        for expression in self._children:
            result += expression.__str__(context) + " "
            
            # If previouse expression completely fills up this measure
            # add a measure sign (this is optional for lilypond, but will
            # be validated if it is there)
            if isinstance(context, RenderContext) and context.position % Fraction(context.time_signature.numerator, context.time_signature.numerator) == 0:
                result += "|\n"
            
        result += "}"
        return result

# Container for multiple voices. Expected to be similar in length
class PolyphonicContext(Expression):

    def __init__(self):
        self.__voices = []
        
    def add(self, voice):
        assert(type(voice) == CompoundExpression)
        self.__voices.append(voice)
            
    # TODO: Try to prevent access to voices
    def voices(self):
        return self.__voices

    def length(self):
        lengths = list(map(lambda x: x.length(), self.__voices))
        longest = max(lengths, default=0)
        return longest

    def is_balanced(self):
        # Checks if all children have equal length (this
        # means that the polyphonic context can be ended)
        lengths = set(map(lambda x: x.length(), self.__voices))
        return len(self.__voices) > 1 and len(lengths) == 1
        
    def merge(self, other):

        assert(isinstance(other, PolyphonicContext))
        assert(self.is_balanced())

        # for now, just randomly add contexts of other to self
        # TODO: keep voices together
        for voice in self.__voices:
            if len(other._PolyphonicContext__voices) > 0:
                voice.merge(other._PolyphonicContext__voices.pop(0))
            
    def sort_function(e):
        # when printing a polyphonic context, sort by average pitch, so that 
        # highest voice is printed first and is drawn with stems up
        pitches = e.pitches()
        return sum(pitches) / len(pitches)
        
    def __str__(self, context = None):
        voices_representations = []
        
        if isinstance(context, RenderContext):
            local_start_position = context.position
        
        for voice in sorted(self.__voices, key=PolyphonicContext.sort_function, reverse=True):
            # each voice starts at the same position
            if isinstance(context, RenderContext):
                context.position = local_start_position
            voices_representations.append(voice.__str__(context))
        
        return "<<\n"+ '\n\\\\\n'.join(voices_representations) + "\n>>"
        
        if isinstance(context, RenderContext):
            context.position = local_start_position + self.length()
    
# A staff is a command followed by an expression that is contained in the staff
class Staff(CompoundExpression):

    def __init__(self, name="new staff"):
        self.__name = name
        super().__init__()

    def __str__(self, context = None):
        
        if isinstance(context, RenderContext): 
            context.position = 0
            context.previous_pitch = None
            context.previous_duration = None

        return "\\new Staff = \"{}\" ".format(self.__name) + super().__str__(context)

# Groups a number of staves. A simple song is expected to have one staff group
class StaffGroup(CompoundExpression):

    def __str__(self, context = None):
        return "\\new StaffGroup <<\n\n{}\n\n>>".format("\n\n".join([e.__str__(context) for e in self._children]))

# Note, Rest, Chord should be immutable
class Rest(Expression):
    
    def __init__(self, duration):
        self.duration = duration
    
    def length(self):
        return self.duration.length()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.duration == other.duration

    def __hash__(self):
        return hash(self.duration)

    def __str__(self, context = None):
        assert(isinstance(self.duration, Duration))
                
        # bad hack: compound durations are represented as:
        # "1~ 4" where the second note implicitly gets the same pitch
        # as the previous. For rests this does not work
        result = 'r' + self.duration.__str__(context).replace('~ ', ' r')
        return result
        
class Note(Expression):
    
    def get_from_midi_note(midi_note, context):
        pitch = Pitch(midi_note.pitch)
        duration = Duration.get_duration(midi_note.end - midi_note.start, context.ticks_per_beat, context.time_signature.denominator)
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

    def __str__(self, context = None):
        assert(isinstance(self.duration, Duration))
        assert(isinstance(self.pitch, Pitch))
        
        result = self.pitch.__str__(context) + self.duration.__str__(context)
        return result

# add helper method to create a chord from note + pitch or chord + pitch
class Chord(Expression):
    
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

    def __str__(self, context = None):
        assert(isinstance(self.duration, Duration))

        pitches = []

        #' '.join([p.__str__(context) for p in sorted(self.pitches)]))
        # bad hack to get relative pitches in a chord to play nice
        for p in sorted(self.pitches):
            pitches.append(p.__str__(context))
            #context.previous_pitch = p.pitch

        result = str("<{}>{}".format(' '.join(pitches), self.duration.__str__(context)))
        if isinstance(context, RenderContext): context.previous_duration = self.duration
        # bad hack to get relative pitches after a chord to play nice
        if isinstance(context, RenderContext): context.previous_pitch = sorted(self.pitches)[0]

        return result

# Converts a midi note number in a note name
# TODO: enharmonics, respect key signature
class Pitch:

    # todo: flats
    noteNames = [ 'c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b' ]

    def __init__(self, pitch):
        # TODO: Rename to midi note number
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

    def __str__(self, context=None):

        octave_string = ""

        # 21 = a0, 12 notes in an octave
        # pitch 60 is a C' (, and ' denote octaves, suchs A0 a,, and C3 c'''
        if isinstance(context, RenderContext) and context.relative:
            
            reference_pitch = context.relative_base
            
            if isinstance(context.previous_pitch, Pitch):
                reference_pitch = context.previous_pitch.pitch

            if reference_pitch - self.pitch > 5:
                octave_string = ","
            elif self.pitch - reference_pitch > 6:
                octave_string = "'"
                
            context.previous_pitch = self
                
        else:
            octave = (self.pitch // 12) - 4
            sign = "'" if (octave > 0) else ","
            octave_string = sign * abs(octave)
            
        return self.noteNames[self.pitch % 12] + octave_string
        
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

    def __str__(self, context = None):
        
        if isinstance(context, RenderContext):
            context.position += self.length()
            
            # type setting optimization: If this note has
            # the same duration as the previous note, you can 
            # omit the duration
            previous_duration = context.previous_duration
            context.previous_duration = self
            if self == previous_duration:
                return ""
                
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
        
        context = RenderContext()
        result = "\\version \"{}\"".format(self.__version)

        if (self.__children != []):
            result += "\n\n"
            for expression in self.__children:
                result += expression.__str__(context)

        return result

class TimeSignature(Expression):
    
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator
        
    def __str__(self, context = None):
        if isinstance(context, ParseContext): context.time_signature = self
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
        self.ticks_per_beat = 0
        self.active_pitches = {}
        
def is_note_on_message(msg):
    return msg.type == 'note_on' and msg.velocity > 0

def is_note_off_message(msg):
    return msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)

def note_on_handler(msg, context):
    # Add pitch to list of active pitches and their start position
    context.active_pitches[msg.note] = context.position
    
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
    start = Position.get_position(midi_note.start, context.ticks_per_beat, context.time_signature.denominator)
    
    if fit_note_in_expression(note, start, context.staff): return
            
    # if we have arrived here we will need a polyphonic context
    if context.polyphonic_context == None:
        context.polyphonic_context = setup_polyphonic_context(context.staff, start)
    
    # try to fit the note into any of the children of the polyphonic context
    for expression in context.polyphonic_context.voices():
        # recalculate start in terms of expression
        local_start = Position(start.length() - (context.staff.length() - context.polyphonic_context.length()))
        note_fits = fit_note_in_expression(note, local_start, expression)

        if note_fits:
            if context.polyphonic_context.is_balanced():
                context.polyphonic_context = None
            return
        
    # if we arrive here the note does not fit in any of the existing voices, create a new one
    expression = CompoundExpression()
    context.polyphonic_context.add(expression)
    local_start = Position(start.length() - (context.staff.length() - context.polyphonic_context.length()))

    if fit_note_in_expression(note, local_start, expression): return
    
def setup_polyphonic_context(expression, start):
    polyphonic_context = PolyphonicContext()
    
    if not isinstance(expression.last(), PolyphonicContext):
        polyphonic_context.add(expression.split_at(start.length()))
   
    # check if last expression is a polyphonic expression. In that
    # case, do not create a new one, but append to existing one
    if isinstance(expression.last(), PolyphonicContext):
        existing_polyphonic_context = expression.last()
        existing_polyphonic_context.merge(polyphonic_context)
        return existing_polyphonic_context
    else:
        expression.add(polyphonic_context)
        return polyphonic_context
   
# TODO: Add to expression class
def fit_note_in_expression(note, start, expression):
    # check if this note can be added to the score as a simple note (no polyphony, no chord)

    # if gap add rest
    if (start.length() > expression.length()):
        expression.add(Rest(Duration(start.length() - expression.length())))

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
                context.time_signature = TimeSignature(msg.numerator, msg.denominator)
                context.ticks_per_beat = midifile.ticks_per_beat

            if is_note_on_message(msg):
                note_on_handler(msg, context)
                
            if is_note_off_message(msg):
                note_off_handler(msg, context)

    return file
    
if __name__ == '__main__':
    [print(convert(mido.MidiFile(arg))) for arg in sys.argv[1:]]