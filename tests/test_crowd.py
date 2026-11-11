import json,math,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from urban_service.crowd_experiment import exposure_interval,union_duration,run_episode

class ExposureTests(unittest.TestCase):
    def test_stationary_inside(self):
        self.assertEqual(exposure_interval((0,0),(0,0),1,.25),(0,.25))
    def test_stationary_outside(self):
        self.assertIsNone(exposure_interval((2,0),(0,0),1,.25))
    def test_exact_crossing_interval(self):
        lo,hi=exposure_interval((-2,0),(1,0),1,4)
        self.assertAlmostEqual(lo,1);self.assertAlmostEqual(hi,3)
    def test_union_has_no_double_counting(self):
        self.assertAlmostEqual(union_duration([(0,.2),(.1,.25),None]),.25)

class BackendTests(unittest.TestCase):
    def test_native_repeatability_and_zero_margin_equivalence(self):
        c=json.loads((ROOT/'configs/crowd_clearance_development.json').read_text())
        c['buffer']['fixed_m']=0
        with tempfile.TemporaryDirectory() as d:
            a=run_episode(c,'circle_crossing','baseline',901,Path(d)/'a')
            b=run_episode(c,'circle_crossing','baseline',901,Path(d)/'b')
            zero=run_episode(c,'circle_crossing','fixed_margin',901,Path(d)/'zero')
            self.assertEqual(a['trace_sha256'],b['trace_sha256'])
            self.assertEqual(a['trace_sha256'],zero['trace_sha256'])
            self.assertEqual(a['initial_fingerprint'],zero['initial_fingerprint'])

if __name__=='__main__':unittest.main()
