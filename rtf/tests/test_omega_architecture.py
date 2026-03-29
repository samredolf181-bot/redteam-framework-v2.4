import unittest

from framework.omega import omega_doctor, omega_registry


class OmegaArchitectureTests(unittest.TestCase):
    def test_manifest_contains_expected_engines(self):
        manifest = omega_registry.manifest()
        names = {engine['name'] for engine in manifest['engines']}
        self.assertIn('rtf-core', names)
        self.assertIn('rtf-graph-engine', names)
        self.assertIn('rtf-worker-cluster', names)
        self.assertGreaterEqual(len(names), 13)

    def test_graph_schema_contains_required_entities_and_relationships(self):
        schema = omega_registry.graph_schema()
        for entity in ['Person', 'Username', 'Email', 'Phone', 'Domain', 'Organization', 'Repository', 'Document', 'Media']:
            self.assertIn(entity, schema['entity_types'])
        for relationship in ['OWNS', 'USES_EMAIL', 'USES_PHONE', 'REGISTERED_WITH', 'CONNECTED_TO', 'POSTED_FROM', 'MENTIONED_IN', 'FOLLOWS', 'ASSOCIATED_WITH']:
            self.assertIn(relationship, schema['required_relationships'])

    def test_doctor_validate_reports_self_healing_commands(self):
        report = omega_doctor.validate()
        self.assertEqual(report['status'], 'ok')
        self.assertIn('doctor', report['self_healing_commands'])
        self.assertIn('repair', report['self_healing_commands'])


if __name__ == '__main__':
    unittest.main()
