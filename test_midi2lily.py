import midi2lily
import unittest
import io
from fractions import Fraction

from mido import MidiFile

class LearningTests(unittest.TestCase):

    def test_mido_open_midi_file(self):

        # open a midi file
        midifile = MidiFile('test-midi-files/canon-d-ostinato.midi')

        #for i, track in enumerate(midifile.tracks):
        #    print('Track {}: {}'.format(i, track.name))
        #    for msg in track:
        #       print(msg)

class LilypondFileTest(unittest.TestCase):

    def test_empty_file(self):
        file = midi2lily.File("1")
        self.assertEqual(str(file), "\\version \"1\"")

    def test_file_with_empty_expression(self):
        file = midi2lily.File("1")
        file.expressions = [ midi2lily.Expression() ]
        self.assertEqual(str(file), "\\version \"1\"\n\n{\n}")

    def test_file_with_staff_with_notes(self):
        file = midi2lily.File("1")
        staff = midi2lily.Staff("trumpet")
        
        staff.children.append(midi2lily.Note(midi2lily.Pitch(79), midi2lily.Duration.get_duration(4, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(79), midi2lily.Duration.get_duration(4, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(79), midi2lily.Duration.get_duration(6, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(77), midi2lily.Duration.get_duration(2, 4, 4)))
        
        staff.children.append(midi2lily.Note(midi2lily.Pitch(76), midi2lily.Duration.get_duration(3, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(74), midi2lily.Duration.get_duration(1, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(72), midi2lily.Duration.get_duration(3, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(76), midi2lily.Duration.get_duration(1, 4, 4)))

        staff.children.append(midi2lily.Note(midi2lily.Pitch(74), midi2lily.Duration.get_duration(4, 4, 4)))
        staff.children.append(midi2lily.Note(midi2lily.Pitch(67), midi2lily.Duration.get_duration(4, 4, 4)))

        file.expressions.append(staff)
        
        self.assertEqual(str(file), "\\version \"1\"\n\n\\new Staff = \"trumpet\" {\ng''4\ng''4\ng''4.\nf''8\ne''8.\nd''16\nc''8.\ne''16\nd''4\ng'4\n}")

class LilypondExpressionTest(unittest.TestCase):

    def test_empty_expression(self):
        expression = midi2lily.Expression()
        self.assertEqual(str(expression), "{\n}")

    def test_expression_with_notes(self):
        
        expression = midi2lily.Expression()

        note = midi2lily.Note(midi2lily.Pitch(60), midi2lily.Duration.get_duration(1, 1, 4))
        expression.children.append(note)

        self.assertEqual(str(expression), "{\nc'4\n}")

    def test_empty_polyphonic_context(self):
        context = midi2lily.PolyphonicContext()

        self.assertEqual(str(context), "<<\n>>")

    def test_polyphonic_context(self):
        context = midi2lily.PolyphonicContext()

        # voice 1
        melody_expression = midi2lily.Expression()

        melody_expression.children.append(midi2lily.Note(midi2lily.Pitch(72), midi2lily.Duration.get_duration(2, 1, 4)))
        
        context.children.append(melody_expression)
        
        # voice 2
        rythm_expression = midi2lily.Expression()

        rythm_expression.children.append(midi2lily.Note(midi2lily.Pitch(64), midi2lily.Duration.get_duration(1, 1, 4)))
        rythm_expression.children.append(midi2lily.Note(midi2lily.Pitch(67), midi2lily.Duration.get_duration(1, 1, 4)))
        
        context.children.append(rythm_expression)
        
        self.assertEqual(str(context), "<<\n{\nc''2\n}\n\\\\\n{\ne'4\ng'4\n}>>")

class LilypondStaffTest(unittest.TestCase):

    def test_empty_staff(self):
        staff = midi2lily.Staff("trumpet")
        self.assertEqual(str(staff), "\\new Staff = \"trumpet\" {\n}")

    def test_staff_with_notes(self):
        staff = midi2lily.Staff("trumpet")
        note = midi2lily.Note(midi2lily.Pitch(60), midi2lily.Duration.get_duration(1, 1, 4))
        staff.children.append(note)
        self.assertEqual(str(staff), "\\new Staff = \"trumpet\" {\nc'4\n}")

class LilypondNoteTest(unittest.TestCase):

    def testDuration(self):

        # Real life Quarter note
        ticks = 384
        ticks_per_beat = 384
        denominator = 4
        duration = midi2lily.Duration.get_duration(ticks, ticks_per_beat, denominator)
        self.assertEqual(str(duration), "4")

        # Real life Half note
        ticks = 384 * 2
        ticks_per_beat = 384
        denominator = 4
        enominator = 4
        duration = midi2lily.Duration.get_duration(ticks, ticks_per_beat, denominator)
        self.assertEqual(str(duration), "2")

        # Simplified whole note
        self.assertEqual(str(midi2lily.Duration.get_duration(4, 1, 4)), "1")

        # Simplified half note
        self.assertEqual(str(midi2lily.Duration.get_duration(2, 1, 4)), "2")

        # Simplified quarter note
        self.assertEqual(str(midi2lily.Duration.get_duration(1, 1, 4)), "4")

        # Simplified 8th note
        self.assertEqual(str(midi2lily.Duration.get_duration(1, 2, 4)), "8")

        # Simplified 16th note
        self.assertEqual(str(midi2lily.Duration.get_duration(1, 4, 4)), "16")

        # dotted notes
        
        # dotted quarter note
        self.assertEqual(str(midi2lily.Duration.get_duration(3, 2, 4)), "4.")

        # dotted 8th note
        self.assertEqual(str(midi2lily.Duration.get_duration(3, 4, 4)), "8.")

        # dotted half note
        self.assertEqual(str(midi2lily.Duration.get_duration(3, 1, 4)), "2.")

        # double dotted quarter note
        self.assertEqual(str(midi2lily.Duration.get_duration(7, 4, 4)), "4..")

        # triple dotted quarter note
        self.assertEqual(str(midi2lily.Duration.get_duration(15, 8, 4)), "4...")

        # notes that cannot be expressed as whole or dotted notes 

        # whole note + one quarter
        self.assertEqual(str(midi2lily.Duration.get_duration(5, 1, 4)), "1~ 4")

        # 2 whole notes + one quarter
        self.assertEqual(str(midi2lily.Duration.get_duration(9, 1, 4)), "1~ 1~ 4")

        # half + 1/8 note
        self.assertEqual(str(midi2lily.Duration.get_duration(5, 2, 4)), "2~ 8")

    def testAFewWholeNotes(self):
        # a few whole notes
        duration = midi2lily.Duration.get_duration(16, 1, 4)
        print('duration: ' + str(duration.fraction))
        self.assertEqual(str(midi2lily.Duration.get_duration(16, 1, 4)), "1~ 1~ 1~ 1")

    def testPitch(self):
        pitch = midi2lily.Pitch(0)
        self.assertEqual(str(pitch), "c,,,,")

        pitch = midi2lily.Pitch(60)
        self.assertEqual(str(pitch), "c'")

        pitch = midi2lily.Pitch(62)
        self.assertEqual(str(pitch), "d'")

    def testPitchEquality(self):
        self.assertTrue(midi2lily.Pitch(60) == midi2lily.Pitch(60))
        self.assertTrue(midi2lily.Pitch(60) != midi2lily.Pitch(62))

    def testNote(self):
        pitch = midi2lily.Pitch(60)
        duration = midi2lily.Duration.get_duration(1, 1, 4)
        note = midi2lily.Note(pitch, duration)
        self.assertEqual(str(note), "c'4")

    def testRest(self):
        duration = midi2lily.Duration.get_duration(1, 1, 4)
        rest = midi2lily.Rest(duration)
        self.assertEqual(str(rest), "r4")

    def testCompoundRest(self):
        duration = midi2lily.Duration.get_duration(5, 1, 4)
        rest = midi2lily.Rest(duration)
        self.assertEqual(str(rest), "r1 r4")

    def testAFewBarsOfRest(self):
        duration = midi2lily.Duration.get_duration(16, 1, 4)
        rest = midi2lily.Rest(duration)
        self.assertEqual(str(rest), "r1 r1 r1 r1")

    def testChord(self):
        pitches = [ midi2lily.Pitch(60), midi2lily.Pitch(62) ]
        duration = midi2lily.Duration.get_duration(1, 1, 4)
        note = midi2lily.Chord(pitches, duration)
        self.assertEqual(str(note), "<c' d'>4")

class LilyPondExpressionLengthTest(unittest.TestCase):

    def testFormatLength(self):
        fraction = Fraction(1,4)

        print(midi2lily.Expression.format_length(fraction))

    def testEmptyExpression(self):
        expression = midi2lily.Expression()
        self.assertEqual(expression.get_length(), 0)

    def testOneNoteExpression(self):
        expression = midi2lily.Expression()

        note = midi2lily.Note(midi2lily.Pitch(60), midi2lily.Duration.get_duration(1, 1, 4))
        expression.children.append(note)

        self.assertEqual(expression.get_length(), Fraction(1, 4))

    def testOneMeasureExpression(self):
        expression = midi2lily.Expression()

        for _ in range(4):
            note = midi2lily.Note(midi2lily.Pitch(60), midi2lily.Duration.get_duration(1, 1, 4))
            expression.children.append(note)

        self.assertEqual(expression.get_length(), Fraction(4, 4))

    def testMultipleMeasursExpression(self):
        expression = midi2lily.Expression()

        for _ in range(12):
            note = midi2lily.Note(midi2lily.Pitch(60), midi2lily.Duration.get_duration(1, 1, 4))
            expression.children.append(note)

        self.assertEqual(expression.get_length(), Fraction(12, 4))

class EndToEndTests(unittest.TestCase):
    
    def test_c(self):
        self.process_file('test-midi-files/c.midi', 'test-midi-files/c.txt')
        
    def test_scale(self):
        self.process_file('test-midi-files/scale.midi', 'test-midi-files/scale.txt')

    def test_chords(self):
        self.process_file('test-midi-files/chords.midi', 'test-midi-files/chords.txt')

    def test_rests(self):
        self.process_file('test-midi-files/rests.midi', 'test-midi-files/rests.txt')

    def test_nachtmusik_intro(self):
        self.process_file('test-midi-files/nachtmusik-intro.midi', 'test-midi-files/nachtmusik-intro.txt')

    def test_nachtmusik_phrase_a(self):
        self.process_file('test-midi-files/nachtmusik-phrase-a.midi', 'test-midi-files/nachtmusik-phrase-a.txt')

    def atest_nachtmusik_phrase_b(self):
        self.process_file('test-midi-files/nachtmusik-phrase-b.midi', 'test-midi-files/nachtmusik-phrase-b.txt')

    def test_canon_d_ostinato(self):
        self.process_file('test-midi-files/canon-d-ostinato.midi', 'test-midi-files/canon-d-ostinato.txt')

    def test_canon_d(self):
        self.process_file('test-midi-files/canon-d-32-bars.midi', 'test-midi-files/canon-d-ostinato.txt', True)

    def process_file(self, test, expected, printOutput=False):

        # open a midi file
        midifile = MidiFile(test)
        result = midi2lily.convert(midifile)
        
        if printOutput:
            print(test)
            print(result)
        expected_file = open(expected)
        expected_result = expected_file.read()
        expected_file.close()
        self.assertEqual(str(result), expected_result)
        
if __name__ == '__main__':
    unittest.main()