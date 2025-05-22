# Copyright (c) 2024, Navari Limited and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from .mpesa_b2c_payment import MPesaB2CPayment
from frappe_mpsa_payments.frappe_mpsa_payments.doctype.mpesa_b2c_payment.custom_exceptions import (
    InformationMismatchError,
)
from unittest.mock import MagicMock


class TestMPesaB2CPayment(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.payment = MPesaB2CPayment()
        self.payment_processor = MPesaB2CPayment()

    def test_generate_uuid_v4(self):
        doc = MPesaB2CPayment()
        uuid1 = doc._generate_uuid_v4()
        uuid2 = doc._generate_uuid_v4()
        self.assertNotEqual(uuid1, uuid2)
        self.assertEqual(len(uuid1), 36)

    def test_validate_employee_with_invalid_commandid(self):
        """
        Test that an InformationMismatchError is raised when the party_type is 'Employee'
        and the commandid is not 'SalaryPayment'. This ensures that the validate method
        correctly enforces the business rule linking party_type to the appropriate commandid.
        """
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Payment",
                "party_type": "Employee",
                "commandid": "SOmeInvalidCommandID",
                "company": "Test Company",
                "mpesa_setting": "Test Setting",
                "remarks": "Test Remarks",
            }
        )

        # Attempt to validate and expect an InformationMismatchError
        with self.assertRaises(InformationMismatchError) as context:
            doc.validate()

        # Check if the error message is as expected
        self.assertEqual(
            str(context.exception),
            "Party Type 'Employee' requires Command ID 'SalaryPayment'",
        )

    def test_validate_party_type_is_not_employee(self):
        """
        Test that no InformationMismatchError is raised when party_type is not 'Employee',
        even if the commandid is not 'SalaryPayment'. This confirms that the commandid
        restriction only applies to Employee party_type.
        """
        self.payment.party_type = "non-Employee value"
        self.payment.commandid = "BusinessPayment"

        try:
            self.payment.validate()
        except InformationMismatchError:
            self.fail("InformationMismatchError was raised unexpectedly.")

    def test_validate_employee_with_salary_payment_passes(self):
        """
        Test that when party_type is 'Employee' and commandid is 'SalaryPayment',
        validation passes without raising an InformationMismatchError.
        This confirms that the allowed combination is accepted.
        """
        self.payment.party_type = "Employee"
        self.payment.commandid = "SalaryPayment"

        try:
            self.payment.validate()
        except InformationMismatchError:
            self.fail(
                "InformationMismatchError was raised unexpectedly for a valid Employee-SalaryPayment combination."
            )

    def test_process_payment_item_success(self):
        """
        Should update the item's payment_status to 'Initiated' and return True
        when the connector returns a successful B2C response.
        """
        item = MagicMock()
        item.name = "ITEM001"
        item.doctype = "MPesa B2C Payment Item"

        connector = MagicMock()
        connector.make_b2c_payment_request.return_value = {"ResponseCode": "0"}

        setting = MagicMock()

        self.payment._prepare_request_data = MagicMock(return_value={"dummy": "data"})

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertEqual(item.payment_status, "Initiated")
        self.assertTrue(result)

    def test_process_payment_item_retry_fails(self):
        """
        Test that _process_payment_item resets the item state on retry and correctly
        handles a failed payment response by updating the error code, description,
        and marking the status as 'Failed'.
        """

        item = MagicMock()
        item.name = "ITEM004"
        item.doctype = "MPesa B2C Payment Item"
        item.error_code = "OLD_ERR"
        item.error_description = "Old error"
        item.payment_status = "Failed"

        connector = MagicMock()
        setting = MagicMock()

        # Simulate failure response
        connector.make_b2c_payment_request.return_value = {
            "ResponseCode": "1",
            "errorCode": "ERR_CODE",
            "errorMessage": "Failed to initiate",
        }

        result = self.payment_processor._process_payment_item(
            item, connector, setting, is_retry=True
        )

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertEqual(item.error_code, "ERR_CODE")
        self.assertEqual(item.error_description, "Failed to initiate")

    def test_process_payment_item_connector_exception(self):
        """
        Test that _process_payment_item correctly handles an unexpected exception
        raised by the connector. The method should set the item's payment_status to
        'Failed', capture the exception message in error_description, and return False.
        """
        item = MagicMock()
        item.name = "ITEM_EXCEPTION"
        item.doctype = "MPesa B2C Payment Item"
        item.payment_status = ""
        item.error_description = ""

        connector = MagicMock()
        setting = MagicMock()

        # Simulate connector throwing an exception
        connector.make_b2c_payment_request.side_effect = Exception("Simulated connector error")

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertIn("Simulated connector error", item.error_description)

    def test_process_payment_item_connector_returns_none(self):
        """
        Test that _process_payment_item handles the case where the connector returns None.
        This should be treated as a failed payment request and the item's payment_status
        should be set to 'Failed' with a generic error description.
        """
        item = MagicMock()
        item.name = "ITEM_NONE"
        item.doctype = "MPesa B2C Payment Item"
        item.payment_status = ""
        item.error_description = ""

        connector = MagicMock()
        setting = MagicMock()

        # Simulate connector returning None
        connector.make_b2c_payment_request.return_value = None

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertEqual(item.error_code, None)
        self.assertEqual(item.error_description, "Unknown error")

    def test_process_payment_item_missing_response_code(self):
        """
        Test that _process_payment_item handles responses without a 'ResponseCode' key.
        The item should be marked as 'Failed' with 'Unknown error' as the description.
        """
        item = MagicMock()
        item.name = "ITEM_NO_CODE"
        item.doctype = "MPesa B2C Payment Item"
        item.payment_status = ""

        connector = MagicMock()
        setting = MagicMock()

        # Response missing 'ResponseCode'
        connector.make_b2c_payment_request.return_value = {
            "errorCode": "NO_CODE",
            "errorMessage": "Missing response code"
        }

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertEqual(item.error_code, "NO_CODE")
        self.assertEqual(item.error_description, "Missing response code")

    def test_process_payment_item_empty_response(self):
        """
        Test that _process_payment_item handles an empty response dictionary from the connector.
        It should treat this as a failure and apply fallback values.
        """
        item = MagicMock()
        item.name = "ITEM_EMPTY"
        item.doctype = "MPesa B2C Payment Item"
        item.payment_status = ""

        connector = MagicMock()
        setting = MagicMock()

        # Connector returns an empty dict
        connector.make_b2c_payment_request.return_value = {}

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertEqual(item.error_code, None)
        self.assertEqual(item.error_description, "Unknown error")

    def test_process_payment_item_missing_name(self):
        """
        Test that _process_payment_item handles an item missing the 'name' attribute.
        It should catch the AttributeError and mark the payment as 'Failed' with the appropriate error message.
        """
        item = MagicMock()
        del item.name
        item.doctype = "MPesa B2C Payment Item"

        connector = MagicMock()
        setting = MagicMock()

        self.payment._prepare_request_data = MagicMock(return_value={"dummy": "data"})

        result = self.payment._process_payment_item(item, connector, setting)

        self.assertFalse(result)
        self.assertEqual(item.payment_status, "Failed")
        self.assertIn("object has no attribute", item.error_description)
