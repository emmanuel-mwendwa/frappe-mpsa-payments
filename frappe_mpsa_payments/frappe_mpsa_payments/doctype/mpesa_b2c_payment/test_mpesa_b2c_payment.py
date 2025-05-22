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
                "commandid": "BusinessPayment",  # Invalid commandid for Employee
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
        self.payment.party_type = "Customer"  # or any non-Employee value
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

        item.payment_status.__setattr__.assert_called_with("Initiated")
        self.assertTrue(result)
