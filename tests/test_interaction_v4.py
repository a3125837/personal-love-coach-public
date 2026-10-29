import importlib.util
from pathlib import Path
import sys
import unittest
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'personal-love-coach/scripts'))
import interaction

class InteractionV4Tests(unittest.TestCase):
    def test_exact_capability_coverage_and_complete_records(self):
        data=interaction.rows('capabilities')
        self.assertEqual(len(data),40)
        self.assertEqual([sum(x['module']==i for x in data) for i in range(1,9)],[8,5,5,5,5,5,4,3])
        ids={x['id'] for x in data}
        self.assertEqual(len(ids),40)
        self.assertEqual(len({x['example'] for x in data}),40)
        for x in data:
            for key in ('name','purpose','trigger','generation','example','situations','pitfalls'):self.assertTrue(x[key])
            self.assertTrue(set(x['combines'])<=ids-{x['id']})
            self.assertIsNone(x['real_case'])
    def test_original_topics_have_balanced_bands(self):
        data=interaction.rows('topics')
        self.assertEqual(len({x['id'] for x in data}),100)
        self.assertEqual(len({x['opening'] for x in data}),100)
        self.assertEqual(Counter(x['band'] for x in data),{'破冰':20,'浅层共鸣':30,'深入了解':30,'浪漫表达':20})
    def test_training_prompt_hides_teaching_answers(self):
        for x in interaction.rows('branches'):
            prompt=interaction.select('branches',x['id'])
            self.assertEqual(set(prompt),{'id','scene','input','source_type'})
            study=interaction.select('branches',x['id'],'study')
            self.assertEqual(len(set(study['candidates'])),3)
            self.assertEqual({b['feedback'] for b in study['branches']},{'positive','ordinary','correction','stop'})
    def test_rejection_never_restarts_pursuit(self):
        row=next(x for x in interaction.rows('branches') if x['scene']=='拒绝')
        self.assertEqual(len({x['action'] for x in row['branches']}),1)
        self.assertTrue(all('收尾' in x['action'] for x in row['branches']))
    def test_invalid_resource_cannot_read_arbitrary_files(self):
        for kind,key,view in [('..','x','prompt'),('branches','../secret','study'),('branches','B01','answer')]:
            with self.assertRaises(ValueError):interaction.select(kind,key,view)
    def test_reproducible_independent_assets(self):
        spec=importlib.util.spec_from_file_location('v4build',ROOT/'development/build_interaction_v4.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for kind,expected in zip(('capabilities','topics','branches'),module.build()):self.assertEqual(interaction.rows(kind),expected)
if __name__=='__main__':unittest.main()
