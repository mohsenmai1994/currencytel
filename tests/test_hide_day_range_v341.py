from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DayRangeRemovedTest(unittest.TestCase):
    def test_ui_does_not_show_day_range(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'assets/js/app.js').read_text(encoding='utf-8')
        css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
        for phrase in ('کف / سقف:', 'بازه روز', 'chartLow', 'chartHigh', 'day-range', 'کمترین روز', 'بیشترین روز'):
            self.assertNotIn(phrase, html+js+css, phrase)
    def test_change_remains(self):
        js=(ROOT/'assets/js/app.js').read_text(encoding='utf-8')
        self.assertIn('changeLabel(q)',js)
        self.assertIn('renderChart()',js)

if __name__ == '__main__': unittest.main()
