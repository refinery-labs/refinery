import stripe
from pyexceptions.billing import CardIsPrimaryException

from utils.general import logit


def get_account_cards(stripe_customer_id):
    # Pull all of the metadata for the cards the customer
    # has on file with Stripe
    cards = stripe.Customer.list_sources(
        stripe_customer_id,
        object="card",
        limit=100,
    )

    # Pull the user's default card and add that
    # metadata to the card
    customer_info = get_stripe_customer_information(
        stripe_customer_id
    )

    for card in cards:
        is_primary = False
        if card["id"] == customer_info["default_source"]:
            is_primary = True
        card["is_primary"] = is_primary

    return cards["data"]


def get_stripe_customer_information(stripe_customer_id):
    return stripe.Customer.retrieve(
        stripe_customer_id
    )


def stripe_create_customer(email, name, phone_number, source_token, metadata_dict):
    # Create a customer in Stripe
    customer = stripe.Customer.create(
        email=email,
        name=name,
        phone=phone_number,
        source=source_token,
        metadata=metadata_dict
    )

    return customer["id"]


def associate_card_token_with_customer_account(stripe_customer_id, card_token):
    # Add the card to the customer's account.
    new_card = stripe.Customer.create_source(
        stripe_customer_id,
        source=card_token
    )

    return new_card["id"]

def set_stripe_customer_default_payment_source(self, stripe_customer_id, card_id):
    customer_update_response = stripe.Customer.modify(
        stripe_customer_id,
        default_source=card_id,
    )

    logit(customer_update_response)


def delete_card_from_account(self, stripe_customer_id, card_id):
    # We first have to pull the customers information so we
    # can verify that they are not deleting their default
    # payment source from Stripe.
    customer_information = get_stripe_customer_information(stripe_customer_id)

    # Throw an exception if this is the default source for the user
    if customer_information["default_source"] == card_id:
        raise CardIsPrimaryException()

    # Delete the card from STripe
    delete_response = stripe.Customer.delete_source(
        stripe_customer_id,
        card_id
    )

    return True
