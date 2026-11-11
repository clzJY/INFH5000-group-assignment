"""Checks for the native collision-classification correction."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from urban_service.runtime import pedestrian_contact

class CollisionAttribution(unittest.TestCase):
    def test_vehicle_tagged_walker_is_counted_in_pedestrian_only_scene(self):
        self.assertTrue(pedestrian_contact({'crash_human':False,'crash_vehicle':True},True))
    def test_mixed_traffic_is_not_automatically_attributed_to_walkers(self):
        self.assertFalse(pedestrian_contact({'crash_human':False,'crash_vehicle':True},False))
    def test_native_human_contact_remains_counted(self):
        self.assertTrue(pedestrian_contact({'crash_human':True},False))

if __name__=='__main__':unittest.main()
