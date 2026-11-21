import unittest
from assistant.logic import normalize, reply, sign_video_for
from recognition.features import FEATURE_COUNT

class TestLogic(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize('Thank you!'), 'thank you')
    def test_reply(self):
        self.assertIn('SignBridge', reply('What is your name?'))
    def test_missing_video(self):
        self.assertIsNone(sign_video_for('nonexistent phrase 123'))
    def test_feature_count(self):
        self.assertEqual(FEATURE_COUNT, 126)

if __name__ == '__main__':
    unittest.main()
