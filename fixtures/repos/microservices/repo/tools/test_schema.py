import os
import unittest

from tools.schema import CONTRACTS_DIR, SchemaError, check_schema, contract, validate

LINE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sku", "quantity"],
    "properties": {
        "sku": {"type": "string", "minLength": 1},
        "quantity": {"type": "integer", "minimum": 1},
        "note": {"type": ["string", "null"]},
    },
}


class ValidateTest(unittest.TestCase):
    def test_a_matching_instance_has_no_error(self):
        self.assertEqual(validate({"sku": "MUG", "quantity": 2, "note": None}, LINE), [])

    def test_a_missing_required_field_is_named(self):
        self.assertEqual(validate({"sku": "MUG"}, LINE), ["$.quantity: required"])

    def test_a_field_the_schema_does_not_declare_is_an_error_when_the_schema_is_strict(self):
        self.assertEqual(validate({"sku": "MUG", "quantity": 1, "color": "red"}, LINE),
                         ["$.color: not declared in the contract"])

    def test_an_open_schema_lets_unknown_fields_through(self):
        self.assertEqual(validate({"anything": 1}, {"type": "object"}), [])

    def test_a_wrong_type_is_reported_once_with_what_was_found(self):
        self.assertEqual(validate({"sku": "MUG", "quantity": "2"}, LINE), ["$.quantity: expected integer, got string"])

    def test_a_boolean_is_not_an_integer_and_a_float_is_not_either(self):
        self.assertEqual(validate(True, {"type": "integer"}), ["$: expected integer, got boolean"])
        self.assertEqual(validate(2.0, {"type": "integer"}), ["$: expected integer, got number"])
        self.assertEqual(validate(2, {"type": "number"}), [])

    def test_a_value_json_does_not_have_is_named_by_its_python_type(self):
        self.assertEqual(validate(("MUG", 1), {"type": "array"}), ["$: expected array, got tuple"])

    def test_minimum_min_length_pattern_const_and_enum(self):
        self.assertEqual(validate({"sku": "", "quantity": 0}, LINE), ["$.sku: shorter than 1", "$.quantity: below 1"])
        self.assertEqual(validate("nobody", {"type": "string", "pattern": "@"}), ["$: does not match '@'"])
        self.assertEqual(validate("order.paid", {"const": "order.created"}), ["$: expected 'order.created'"])
        self.assertEqual(validate("x", {"enum": ["a", "b"]}), ["$: 'x' is not one of ['a', 'b']"])

    def test_array_items_are_checked_with_their_index(self):
        lines = {"type": "array", "minItems": 1, "items": LINE}
        self.assertEqual(validate([], lines), ["$: fewer than 1 item(s)"])
        self.assertEqual(validate([{"sku": "MUG", "quantity": 1}, {"sku": "MUG"}], lines), ["$[1].quantity: required"])


class SchemaIsCheckedTest(unittest.TestCase):
    def test_an_unsupported_keyword_is_refused_not_ignored(self):
        with self.assertRaises(SchemaError) as raised:
            validate({}, {"type": "object", "oneOf": []})
        self.assertIn("oneOf", str(raised.exception))

    def test_an_unsupported_keyword_is_refused_even_where_no_instance_goes(self):
        nested = {"type": "object", "properties": {"lines": {"type": "array", "items": {"maxLength": 3}}}}
        with self.assertRaises(SchemaError) as raised:
            validate({}, nested)
        self.assertIn("$.lines[]", str(raised.exception))

    def test_an_unknown_type_and_a_schema_valued_additional_properties_are_refused(self):
        with self.assertRaises(SchemaError):
            check_schema({"type": "date"})
        with self.assertRaises(SchemaError):
            check_schema({"type": "object", "additionalProperties": {"type": "string"}})

    def test_every_contract_of_the_repository_loads(self):
        names = []
        for folder, _dirs, files in os.walk(CONTRACTS_DIR):
            for name in sorted(files):
                if name.endswith(".json"):
                    names.append(os.path.relpath(os.path.join(folder, name), CONTRACTS_DIR)[: -len(".json")])
        self.assertGreaterEqual(len(names), 4)
        for name in names:
            with self.subTest(contract=name):
                self.assertEqual(contract(name.replace(os.sep, "/")).get("additionalProperties"), False,
                                 "a contract is strict: what it does not declare is refused")


if __name__ == "__main__":
    unittest.main()
