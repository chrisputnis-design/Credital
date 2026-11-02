import subprocess
import sys
import unittest


class PlayTests(unittest.TestCase):
    def test_scripted_session(self):
        inp = "c\n" * 12 + "r 6\nf\nbogus\np\na\nq\n"
        out = subprocess.run([sys.executable, "-m", "pokerbot.play", "--seed", "1"], input=inp,
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("=== Hand 1", out.stdout)
        self.assertIn("session:", out.stdout)
        self.assertIn("Bye.", out.stdout)


if __name__ == "__main__":
    unittest.main()
