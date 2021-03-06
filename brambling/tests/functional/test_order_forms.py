from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from mock import patch
import stripe

from brambling.forms.orders import (
    STRIPE_API_ERROR,
    OneTimePaymentForm,
    SavedCardPaymentForm,
    DwollaPaymentForm,
    CheckPaymentForm,
)
from brambling.models import Transaction
from brambling.payment.core import TEST, InvalidAmountException
from brambling.tests.factories import (
    OrderFactory,
    PersonFactory,
    CardFactory,
    DwollaUserAccountFactory,
    DwollaOrganizationAccountFactory,
    EventFactory,
)


STRIPE_CHARGE = stripe.Charge.construct_from({
    "amount": 4215,
    "amount_refunded": 0,
    "application_fee": "fee_8ZDpRjN3NgSvSM",
    "balance_transaction": {
        "amount": 4215,
        "available_on": 1465430400,
        "created": 1464910662,
        "currency": "usd",
        "description": None,
        "fee": 257,
        "fee_details": [
            {
                "amount": 105,
                "application": "ca_4chEaXTzoWf7wlHdukG9gYj2n4ivgvpR",
                "currency": "usd",
                "description": "Dancerfly application fee",
                "type": "application_fee"
            },
            {
                "amount": 152,
                "application": None,
                "currency": "usd",
                "description": "Stripe processing fees",
                "type": "stripe_fee"
            }
        ],
        "id": "txn_18I5NiKDDJKt8tvufAp4pa0i",
        "net": 3958,
        "object": "balance_transaction",
        "source": "ch_18I5NiKDDJKt8tvuixpSiCYN",
        "sourced_transfers": {
            "data": [],
            "has_more": False,
            "object": "list",
            "total_count": 0,
            "url": "/v1/transfers?source_transaction=ch_18I5NiKDDJKt8tvuixpSiCYN"
        },
        "status": "pending",
        "type": "charge"
    },
    "captured": True,
    "created": 1464910662,
    "currency": "usd",
    "customer": None,
    "description": None,
    "destination": None,
    "dispute": None,
    "failure_code": None,
    "failure_message": None,
    "fraud_details": {},
    "id": "ch_18I5NiKDDJKt8tvuixpSiCYN",
    "invoice": None,
    "livemode": False,
    "metadata": {
        "event": "Test event",
        "order": "000001"
    },
    "object": "charge",
    "order": None,
    "paid": True,
    "receipt_email": None,
    "receipt_number": None,
    "refunded": False,
    "refunds": {
        "data": [],
        "has_more": False,
        "object": "list",
        "total_count": 0,
        "url": "/v1/charges/ch_18I5NiKDDJKt8tvuixpSiCYN/refunds"
    },
    "shipping": None,
    "source": {
        "address_city": None,
        "address_country": None,
        "address_line1": None,
        "address_line1_check": None,
        "address_line2": None,
        "address_state": None,
        "address_zip": None,
        "address_zip_check": None,
        "brand": "Visa",
        "country": "US",
        "customer": None,
        "cvc_check": "pass",
        "dynamic_last4": None,
        "exp_month": 12,
        "exp_year": 2050,
        "fingerprint": "ER8TJFn2KwxGXmA8",
        "funding": "credit",
        "id": "card_18I5NiKDDJKt8tvuGIPdNdWu",
        "last4": "4242",
        "metadata": {},
        "name": None,
        "object": "card",
        "tokenization_method": None
    },
    "source_transfer": None,
    "statement_descriptor": None,
    "status": "succeeded"
}, 'FAKE')


DWOLLA_CHARGE = {
    u'Amount': 42.15,
    u'ClearingDate': u'',
    u'Date': u'2015-01-31T02:41:38Z',
    u'Destination': {u'Id': u'FAKE_DEST',
                     u'Image': u'http://uat.dwolla.com/avatars/FAKE_DEST',
                     u'Name': u'Blah blah blah',
                     u'Type': u'Dwolla'},
    u'DestinationId': u'FAKE_DEST',
    u'DestinationName': u'Blah blah blah',
    u'Fees': [{u'Amount': 0.25, u'Id': 827529, u'Type': u'Dwolla Fee'},
              {u'Amount': 1.05, u'Id': 827530, u'Type': u'Facilitator Fee'}],
    u'Id': 827527,
    u'Metadata': None,
    u'Notes': u'',
    u'OriginalTransactionId': None,
    u'Source': {u'Id': u'FAKE_SOURCE',
                u'Image': u'http://uat.dwolla.com/avatars/FAKE_SOURCE',
                u'Name': u'John Doe',
                u'Type': u'Dwolla'},
    u'SourceId': u'FAKE_SOURCE',
    u'SourceName': u'John Doe',
    u'Status': u'processed',
    u'Type': u'money_received',
    u'UserType': u'Dwolla'
}

DWOLLA_SOURCES = [
    {
        "Id": "Balance",
        "Name": "My Dwolla Balance",
        "Type": "",
        "Verified": "true",
        "ProcessingType": ""
    },
]


class OneTimePaymentFormTestCase(TestCase):

    def setUp(self):
        self.event = EventFactory(api_type=TEST)
        self.order = OrderFactory(event=self.event)
        self.person = PersonFactory()
        self.token = 'FAKE_TOKEN'

    @patch('brambling.forms.orders.stripe_charge')
    def test_successful_charge(self, stripe_charge):
        stripe_charge.return_value = STRIPE_CHARGE
        form = OneTimePaymentForm(order=self.order, amount=Decimal('42.15'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertFalse(form.errors)
        stripe_charge.assert_called_once_with(
            self.token,
            amount=Decimal('42.15'),
            event=self.event,
            order=self.order,
        )
        txn = form.save()
        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.event, self.event)
        self.assertEqual(txn.amount, Decimal('42.15'))
        self.assertEqual(txn.application_fee, Decimal('1.05'))
        self.assertEqual(txn.processing_fee, Decimal('1.52'))

    def test_negative_charge_adds_errors(self):
        form = OneTimePaymentForm(order=self.order, amount=Decimal('-1.00'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'],
                         ["Cannot charge an amount less than zero."])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_carderror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.CardError(error_message, 1, 1)
        form = OneTimePaymentForm(order=self.order, amount=Decimal('42.15'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_apierror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.APIError(error_message, 1, 1)
        form = OneTimePaymentForm(order=self.order, amount=Decimal('42.15'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [STRIPE_API_ERROR])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_invalidamountexception(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = InvalidAmountException(error_message)
        form = OneTimePaymentForm(order=self.order, amount=Decimal('42.15'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_invalidrequesterror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.InvalidRequestError(error_message, 1)
        form = OneTimePaymentForm(order=self.order, amount=Decimal('42.15'),
                                  data={'token': self.token}, user=self.person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])


class SavedCardPaymentFormTestCase(TestCase):

    def setUp(self):
        self.person = PersonFactory(stripe_test_customer_id='FAKE_CUSTOMER_ID')
        self.order = OrderFactory(person=self.person)
        self.event = self.order.event
        self.card = CardFactory(is_saved=True)
        self.person.cards.add(self.card)
        self.person.save()

    @patch('brambling.forms.orders.stripe_charge')
    def test_successful_charge(self, stripe_charge):
        stripe_charge.return_value = STRIPE_CHARGE
        form = SavedCardPaymentForm(self.order, Decimal('42.15'),
                                    data={'card': self.card.pk})
        self.assertTrue(form.is_bound)
        self.assertFalse(form.errors)
        stripe_charge.assert_called_once_with(
            self.card.stripe_card_id,
            amount=Decimal('42.15'),
            event=self.event,
            order=self.order,
            customer='FAKE_CUSTOMER_ID'
        )
        txn = form.save()
        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.event, self.event)
        self.assertEqual(txn.amount, Decimal('42.15'))
        self.assertEqual(txn.application_fee, Decimal('1.05'))
        self.assertEqual(txn.processing_fee, Decimal('1.52'))

    def test_negative_amount_adds_errors(self):
        form = SavedCardPaymentForm(self.order, Decimal('-1.00'),
                                    data={'card': self.card.pk})

        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'],
                         ["Cannot charge an amount less than zero."])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_carderror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.CardError(error_message, 1, 1)
        form = SavedCardPaymentForm(order=self.order, amount=Decimal('42.15'),
                                    data={'card': self.card.pk})
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_apierror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.APIError(error_message, 1, 1)
        form = SavedCardPaymentForm(order=self.order, amount=Decimal('42.15'),
                                    data={'card': self.card.pk})
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [STRIPE_API_ERROR])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_invalidamountexception(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = InvalidAmountException(error_message)
        form = SavedCardPaymentForm(order=self.order, amount=Decimal('42.15'),
                                    data={'card': self.card.pk})
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])

    @patch('brambling.forms.orders.stripe_charge')
    def test_handles_invalidrequesterror(self, stripe_charge):
        error_message = "Hi"
        stripe_charge.side_effect = stripe.error.InvalidRequestError(error_message, 1)
        form = SavedCardPaymentForm(order=self.order, amount=Decimal('42.15'),
                                    data={'card': self.card.pk})
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [error_message])


class DwollaPaymentFormTestCase(TestCase):

    @patch('brambling.forms.orders.dwolla_get_sources')
    def test_negative_charge_adds_errors(self, dwolla_get_sources):
        dwolla_get_sources.return_value = DWOLLA_SOURCES
        order = OrderFactory()
        event = order.event
        event.organization.dwolla_test_account = DwollaOrganizationAccountFactory()
        event.organization.save()
        person = PersonFactory()
        person.dwolla_test_account = DwollaUserAccountFactory()
        person.save()
        pin = '1234'
        source = 'Balance'
        form = DwollaPaymentForm(order=order, amount=Decimal('-1.00'),
                                 data={'dwolla_pin': pin, 'source': source},
                                 user=person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'],
                         ["Cannot charge an amount less than zero."])

    @patch('brambling.forms.orders.dwolla_get_sources')
    @patch('brambling.forms.orders.dwolla_charge')
    def test_dwolla_payment_form(self, dwolla_charge, dwolla_get_sources):
        dwolla_charge.return_value = DWOLLA_CHARGE
        dwolla_get_sources.return_value = DWOLLA_SOURCES
        order = OrderFactory()
        event = order.event
        event.organization.dwolla_test_account = DwollaOrganizationAccountFactory()
        event.organization.save()
        person = PersonFactory()
        person.dwolla_test_account = DwollaUserAccountFactory()
        person.save()
        pin = '1234'
        source = 'Balance'
        form = DwollaPaymentForm(order=order, amount=Decimal('42.15'), data={'dwolla_pin': pin, 'source': source}, user=person)
        self.assertTrue(form.is_bound)
        self.assertFalse(form.errors)
        dwolla_charge.assert_called_once_with(
            account=person.dwolla_test_account,
            amount=42.15,
            event=event,
            pin=pin,
            source=source,
            order=order,
        )
        txn = form.save()
        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.event, event)
        self.assertEqual(Decimal(str(txn.amount)), Decimal('42.15'))
        self.assertEqual(Decimal(str(txn.application_fee)), Decimal('1.05'))
        self.assertEqual(Decimal(str(txn.processing_fee)), Decimal('0.25'))

    @patch('brambling.forms.orders.dwolla_get_sources')
    @patch('dwolla.oauth.refresh')
    def test_dwolla_payment_form_handles_valueerror(self, oauth_refresh, dwolla_get_sources):
        oauth_refresh.return_value = {
            'error': 'access_denied',
            'error_description': 'Arbitrary error code.'
        }
        dwolla_get_sources.return_value = DWOLLA_SOURCES
        order = OrderFactory()
        order.event.organization.dwolla_test_account = DwollaOrganizationAccountFactory(
            access_token_expires=timezone.now() - timedelta(1)
        )
        order.event.organization.save()
        person = PersonFactory()
        person.dwolla_test_account = DwollaUserAccountFactory()
        person.save()
        pin = '1234'
        source = 'Balance'
        form = DwollaPaymentForm(order=order, amount=Decimal('42.15'), data={'dwolla_pin': pin, 'source': source}, user=person)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.errors)
        self.assertEqual(form.errors['__all__'], [oauth_refresh.return_value['error_description']])


class CheckPaymentFormTestCase(TestCase):

    def test_check_payment_form(self):
        order = OrderFactory()
        event = order.event
        form = CheckPaymentForm(order=order, amount=Decimal('42.15'), data={})
        self.assertTrue(form.is_bound)
        self.assertFalse(form.errors)
        txn = form.save()
        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.event, event)
        self.assertEqual(txn.amount, Decimal('42.15'))
        self.assertEqual(txn.application_fee, Decimal('0'))
        self.assertEqual(txn.processing_fee, Decimal('0'))
