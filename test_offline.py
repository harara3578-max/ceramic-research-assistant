import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def get_script(stem):
    spec = importlib.util.spec_from_file_location(stem, ROOT / 'scripts' / (stem + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class TestSkill(unittest.TestCase):
    def test_frontmatter(self):
        txt = (ROOT/'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(txt.startswith('---\nname: ceramic-research-assistant\n'))
        self.assertIn('description:', txt)

    def test_eda(self):
        m = get_script('analyze_experiments')
        rows, cols = m.read_rows(ROOT/'assets/example_experiments.csv')
        r = m.analyze(rows, cols)
        self.assertEqual(r['n_rows'], 9)
        self.assertEqual(r['n_unique_sample_ids'], 9)
        self.assertIn('epsilon_r', r['metrics'])
        self.assertGreater(r['metrics']['epsilon_r']['overall']['mean'], 2200)
        self.assertIn('dopant_mol_pct', r['factor_groups'])

    def test_hypotheses(self):
        m = get_script('validate_hypotheses')
        source = json.loads((ROOT/'assets/example_hypotheses.json').read_text(encoding='utf-8'))
        self.assertEqual(m.validate(source), [])
        source['hypotheses'][0]['supporting_observation_ids'] = ['nonexistent']
        self.assertTrue(m.validate(source))

    def test_xrd(self):
        m = get_script('xrd_peak_screen')
        peaks = m.screen(m.load_data(ROOT/'assets/example_xrd.csv'))
        self.assertGreaterEqual(len(peaks), 3)
        self.assertTrue(any(abs(p['two_theta_deg']-31.5)<0.2 for p in peaks))

    def test_doe(self):
        m = get_script('plan_experiments')
        spec = json.loads((ROOT/'assets/example_design.json').read_text(encoding='utf-8'))
        rows, fields = m.plan(spec)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows, m.plan(spec)[0])
        self.assertIn('run_id', fields)
        spec['human_approval_required'] = False
        with self.assertRaises(ValueError):
            m.plan(spec)

    def test_no_network_imports(self):
        import ast
        blocked = {'socket', 'urllib', 'requests', 'http', 'ftplib', 'subprocess', 'pip', 'boto3', 'paramiko'}
        for f in (ROOT/'scripts').glob('*.py'):
            tree = ast.parse(f.read_text(encoding='utf-8'))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(n.name.split('.')[0] for n in node.names)
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split('.')[0])
            self.assertFalse(imported & blocked, f'{f.name}: {imported & blocked}')

if __name__ == '__main__':
    unittest.main()
