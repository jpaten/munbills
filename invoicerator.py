from __future__ import print_function

import string
import stripe
import datetime
import requests
import json

import os.path
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CONFIG_FILE = "../stripe_keys_test.json"

with open(CONFIG_FILE, "r") as f:
    config_and_keys = json.load(f)

stripe.api_key = config_and_keys["api_key"]
CARD_FEE = config_and_keys["card_fee"]
DELEGATION_FEE = config_and_keys["delegation_fee"]
ONLINE_DEL_FEE = config_and_keys["online_fees"]
IP_DEL_FEE = config_and_keys["ip_fees"]
EIN = config_and_keys["EIN"]
T1_COUPON = config_and_keys["T1_coupon"]

DAYS_LEFT = config_and_keys["default_time"]
REGISTRATION_START = datetime.datetime(*config_and_keys["registration_start"])

CARD_HTML = config_and_keys["card_email"]
CHECK_HTML = config_and_keys["check_email"]
EXTERNAL_EMAIL = config_and_keys["external_email"]
FINANCE_EMAIL = config_and_keys["finance_email"]
EMAIL_SUBJECT = config_and_keys["email_subject"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]

date_from_american = lambda date: datetime.datetime(int(date[2]), int(date[0]), int(date[1]))


def main():
    # Parse input in form of a row copied from the Registration Sheet
    line = input(
        f"Welcome to MUNBills, currently running in {config_and_keys['key_type']} mode! Please copy in a row from the reg sheet\n")
    line_list = line.split("\t")
    input_keys = config_and_keys["input"]
    try: #TODO: add validation
        school = get_text_from_sheet(line_list,"delegation_name")
        t1 = get_binary_from_sheet(line_list, "discount", required=False, default=False)
        ind = get_binary_from_sheet(line_list, "no_delegation_fee", required=False, default=False)
        adv_name = get_text_from_sheet(line_list, "head_del_name")
        address = get_text_from_sheet(line_list, "billing_address")
        email = get_text_from_sheet(line_list, "email")
        phone = get_text_from_sheet(line_list, "phone", required=False)
        period = get_text_from_sheet(line_list, "registration_period")
        reg_date = get_text_from_sheet(line_list, "registration_date")
        ip_dels = get_int_from_sheet(line_list, "in_person_delegate_count", required=False)
        ol_dels = get_int_from_sheet(line_list, "online_delegate_count", required=False)
        if ip_dels + ol_dels <= 0:
            print("No delegates seem to be registered!")
            exit(1)
        card = get_binary_from_sheet(line_list, "card", options=["Credit Card", "Check"])
        amountToInvoice = get_text_from_sheet(line_list, "expected_cost")
        deadline = get_text_from_sheet(line_list, "deadline", required=False)
        daysLeft = get_text_from_sheet(line_list, "days_left", required=False, default=str(DAYS_LEFT))
        if daysLeft != "PAID" and int(daysLeft) < 0:
            print("Invoice due in the past! Please correct!")
            exit(1)
    except IndexError:
        print("Bad entry, did you copy from the right place?")
        exit(1)
    # Create or retrieve Customer
    # First extract address
    goodAddress = input(f"Address given as {address}, is this correct(Y/n)?\n")
    if goodAddress == "Y":
        cust_address = get_auto_address(address)
    else:
        cust_address = get_manual_address()

    # Check for existing customer
    found_customers = stripe.Customer.search(query=f"name~ '{adv_name}' AND email: '{email}'")
    if found_customers["data"]:
        if len(found_customers["data"]) > 1:
            for i in range(len(found_customers["data"])):
                made_date = datetime.date.fromtimestamp(found_customers["data"][i].created)
                print(
                    f"Customer {i}, generated on {made_date.year}-{made_date.month}-{made_date.day}:\n {found_customers['data'][i]}")
            while True:
                customer_number = input("Many customers found, please type the number of the customer to use")
                try:
                    customer = found_customers["data"][int(customer_number)]
                    break
                except ValueError:
                    print("Input was not a number, try again")
                except IndexError:
                    print("Not a valid customer, try again")
            to_delete = input("Delete other customers? (Y/n)\n")
            if to_delete == "Y":
                for i in range(len(found_customers["data"])):
                    if i != int(customer_number):
                        stripe.Customer.delete(found_customers["data"][i].id)
        else:
            customer = found_customers["data"][0]
        customer = stripe.Customer.modify(
            customer.id,
            address=cust_address,
            description=school)

    else:
        customer = stripe.Customer.create(
            description=school,
            email=email,
            name=adv_name,
            address=cust_address
        )

    # Invoice is already paid, so get a receipt
    if daysLeft == "PAID":
        # Check it was actually paid
        split_reg_date = reg_date.split("/")
        if len(split_reg_date) == 3:
            datetime_reg_date = date_from_american(split_reg_date)
        else:
            print("Date not formatted properly")
            exit(1)
        paid_charges = stripe.Charge.search(
            query=f"customer: '{customer.id}' AND status: 'succeeded' AND created > '{int(datetime_reg_date.timestamp())}'")  # TODO: This doesn't work
        if not paid_charges["data"]:
            print(f"Invoice marked as paid, but no paid invoices exist from this cycle. Customer ID is '{customer.id}")
            exit(2)
        elif len(paid_charges["data"]) == 1:
            receipt = paid_charges["data"][0].receipt_url
            invoice = stripe.Invoice.retrieve(paid_charges["data"][0].invoice)
            print(f"Invoice {invoice.number} marked as paid, receipt url:\n {receipt}")
        else:
            print("Multiple paid charges")
            for i in paid_charges["data"]:
                receipt = i.receipt_url
                invoice = stripe.Invoice.retrieve(i.invoice)
                print(f"Invoice {invoice.number} marked as paid, receipt url: {receipt}")
        exit(0)
    # Check if customer has outstanding invoices
    open_customer_payments = stripe.PaymentIntent.search(
        query=f"customer: '{customer.id}' AND status: 'requires_payment_method'", limit=99)
    print(f"Customer has {len(open_customer_payments['data'])} open payments")
    if len(open_customer_payments["data"]) == 1:
        while True:
            decision = input("""Customer has existing open invoice. Select an option:
             (V)oid invoice, (R)eissue invoice by voiding it and continuing, (C)ontinue as usual, or (Q)uit?""")
            if decision in ["V", "R", "C", "Q"]:
                break
            else:
                print("Not a valid option, please try again")
        if decision in ["V", "R"]:
            print("Voiding invoice")
            stripe.Invoice.void_invoice(open_customer_payments["data"][0].invoice)
        if decision in ["V", "Q"]:
            exit(0)
    elif len(open_customer_payments["data"]) > 1:
        decision = input(
            "Customer has at least {len(open_customer_payments['data'])} invoices. This might be bad! Please select an option:\n(C)ontinue as usual, creating another invoice or (Q)uit and review invoices on Stripe")
        if decision == "Q":
            exit(0)

    # Delegation Fee
    if ind and ip_dels + ol_dels > 1:
        input("WARNING: multiple delegates registered to a no delegation fee delegation, press enter to confirm, or quit")
    elif not ind:
        stripe.InvoiceItem.create(
            customer=customer,
            price=DELEGATION_FEE
        )

    # Per delegate fees
    if ip_dels > 0:
        stripe.InvoiceItem.create(
            quantity=ip_dels,
            customer=customer,
            price=IP_DEL_FEE[period]  # TODO: add validation
        )
    if ol_dels > 0:
        stripe.InvoiceItem.create(
            quantity=ol_dels,
            customer=customer,
            price=ONLINE_DEL_FEE[period]  # TODO: Validation
        )

    # Set due date
    days_left = 30
    if deadline != "":
        deadline_split = deadline.split("/")
        # Will break in y3k :p
        given_year = int(deadline_split[2])
        real_year = 2000 + given_year if given_year < 1000 else given_year
        deadline_date = datetime.date(year=real_year, month=int(deadline_split[0]),
                                      day=int(deadline_split[1]))
        days_left = (deadline_date - datetime.date.today()).days
    else:
        deadline_date = datetime.date.today() + datetime.timedelta(days=30)
    invoice = stripe.Invoice.create(
        account_tax_ids=[EIN],
        auto_advance=False,
        collection_method="send_invoice",
        customer=customer,
        days_until_due=days_left,
        payment_settings={"payment_method_types": ["ach_debit"]}
    )
    if card:
        invoice = stripe.Invoice.modify(invoice.id,
                                        default_tax_rates=[CARD_FEE],
                                        payment_settings={"payment_method_types": ["card"]},
                                        description="BruinMUN 2022 Registration.",
                                        footer="Online payments are subject to an additional 3% payment processing fee. If you wish to pay by check, please let us know and we will issue a new invoice.")
    else:
        invoice = stripe.Invoice.modify(invoice.id,
                                        footer="Online payments are subject to an additional 3% payment processing fee. If you wish to pay online, please let us know and we will issue a new invoice.")
    if t1:
        invoice = stripe.Invoice.modify(invoice.id, discounts=[{"coupon": T1_COUPON}])

    # Finalize invoice
    input(f"Press enter to confirm address or quit:\n {invoice['customer_address']})")  # TODO: delete draft invoices
    if float(invoice["total"]) / 100 != float(amountToInvoice[1:].replace(",", "")):
        input(
            f"WARNING: Invoice for ${float(invoice['total']) / 100}, sheet calculated as {amountToInvoice}, press enter to finalize or quit")
    else:
        input(
            f"Press enter to finalize invoice of {ip_dels} IP dels & {ol_dels} OL dels for ${float(invoice['total']) / 100}")
    invoice = stripe.Invoice.finalize_invoice(invoice, auto_advance=False)
    print(f"Invoice info:\n {invoice})")

    # Download invoice
    invoice_bytes = requests.get(invoice.invoice_pdf)
    invoice_filename = f"GeneratedInvoices/{invoice['number']}.pdf"
    with open(invoice_filename, "wb") as file:
        file.write(invoice_bytes.content)
    print(f"Invoice link: {invoice.hosted_invoice_url}")
    with open("GeneratedInvoices/links.txt", "a") as file:
        file.write(f"{invoice.number} — {customer.description}: {invoice.hosted_invoice_url}\n")

    line_list[14] = "$" + str(float(invoice["total"]) / 100)
    today = datetime.date.today()
    line_list[11] = f"{today.month}/{today.day}/{today.year}"

    # Emailing bit
    email_start = input("Would you like to create a draft? (Y/n)\n")
    if email_start != "Y":
        print("Stopping")
        exit(0)
    else:
        scopes = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.compose']
        # Use old credentials or authorize new ones
        # This bit was just copied from a tutorial :p
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('../token.json'):
            creds = Credentials.from_authorized_user_file('../token.json', scopes)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    '../credentials.json', scopes, redirect_uri="https://bruinmun.org/")
                creds = flow.run_local_server(port=8000)
            # Save the credentials for the next run
            with open('../token.json', 'w') as token:
                token.write(creds.to_json())

        # Create api client
        service = build('gmail', 'v1', credentials=creds)

        # Get email html
        html_file = CARD_HTML if card else CHECK_HTML
        with open(html_file, "r") as html_file:
            html_base = html_file.read()
        del_intro = "your delegation" if ind else "you"
        on_campus = "on campus" if ol_dels == 0 else ""
        registration_type = {"E": "Early Registration", "R": "Regular Registration", "L": "Late Registration"}[period]
        date = f"{MONTHS[deadline_date.month - 1]} {deadline_date.day}, {deadline_date.year}"
        if card:
            html_text = html_base.format(
                link=invoice.hosted_invoice_url,
                del_intro=del_intro,
                on_campus=on_campus,
                registration_type=registration_type,
                date=date
            )
        else:
            html_text = html_base.format(
                del_intro=del_intro,
                on_campus=on_campus,
                registration_type=registration_type,
                date=date
            )
        with open("../current_email.html", "w") as f:
            f.write(html_text)
        print("Email made, please check current_email.html")

        # Get recipients
        make_draft = input("Confirm draft (Y/n)\n")
        recipients = [email]
        if make_draft != "Y":
            exit(0)
        while True:
            extra = input("Please enter any additional emails, or press enter to stop\n")
            if extra:
                recipients.append(extra)
            else:
                break

        # Make email
        message = EmailMessage()
        message.add_alternative(html_text, subtype="html")
        message["To"] = ", ".join(recipients)
        message["cc"] = EXTERNAL_EMAIL
        message["From"] = FINANCE_EMAIL
        message["Subject"] = EMAIL_SUBJECT
        with open(invoice_filename, "rb") as f:
            message.add_attachment(f.read(), maintype="application", subtype="pdf",
                                   filename=f"Invoice-{invoice.number}.pdf")
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }

        # Create draft!!
        draft = service.users().drafts().create(userId="me",
                                                body={"message": create_message}).execute()
        print(F'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')
        print(message.get_content_type())


def get_auto_address(address):
    cust_address = {}
    address_fix = address.replace(", ", ",")
    address_split = address_fix.split(",")
    try:
        cust_address["line1"] = string.capwords(address_split[0])
        line_two = input("If the address has a line 2 enter it now, otherwise press enter\n")
        if line_two:
            cust_address["line2"] = line_two
            cust_address["line1"] = input("Please enter the address line 1\n")
        cust_address["city"] = string.capwords(address_split[1])

        address_rest = address_split[2].split()
        cust_address["state"] = string.capwords(address_rest[0])  # TODO: validation
        try:
            cust_address["postal_code"] = int(address_rest[1].split("-")[0])
            cust_address["country"] = " ".join(address_rest[2:])
        except ValueError:
            cust_address["state"] = string.capwords(address_rest[0] + " " + address_rest[1])
            cust_address["postal_code"] = address_rest[2]
            cust_address["country"] = " ".join(address_rest[3:])
    except IndexError:
        print("Address incomplete, please enter manually")
        cust_address = get_manual_address()
    except ValueError:
        print("Bad address, please enter manually")
        cust_address = get_manual_address()
    if cust_address["country"].lower() in ["us", "united states", "united states of america", "usa", "america"]:
        cust_address["country"] = "US"
    else:
        cust_address["country"] = input("Country not detectable, enter 2 letter code")
    if cust_address["state"].lower() in ["california", "ca"]:
        cust_address["state"] = "California"
    else:
        new_state = input(
            F"Address state given as {cust_address['state']}. Enter new state(full) or press return to use entered state")
        if new_state not in string.whitespace:
            cust_address["state"] = new_state
    return cust_address


def get_manual_address():
    cust_address = {}
    address_done = False
    while not address_done:
        cust_address["line1"] = input("Enter Address Line 1\n")
        cust_address["line2"] = input("Enter Address Line 2\n")
        cust_address["city"] = input("Enter City\n")
        cust_address["state"] = input("Enter state / province (complete)\n")
        cust_address["country"] = input("Enter Country (2 letter code)\n")
        cust_address["postal_code"] = input("Enter postcode\n")
        print(cust_address)
        address_check = input("Is this a good address(Y/n)?\n")
        if address_check == "Y":
            address_done = True
    return cust_address


def get_text_from_sheet(line_list, key, source=config_and_keys["input"], required=True, default=""):
    if len(line_list) > source[key] > -1 and line_list[source[key]] != "":
        return line_list[source[key]]
    elif not required:
        return default
    else:
        print(f"Value {key} not found in input")
        exit(1)


def get_int_from_sheet(line_list, key, source=config_and_keys["input"], required=True, default=-1):
    if len(line_list) > source[key] > -1 and line_list[source[key]].isnumeric():
        return int(line_list[source[key]])
    elif not required:
        return default
    else:
        print(f"Value {key} not found in input")
        exit(1)


def get_binary_from_sheet(line_list, key, options=("1", "0"), source=config_and_keys["input"], required=True, default=False):
    if len(line_list) > source[key] > -1 and line_list[source[key]] in options:
        return True if line_list[source[key]] == options[0] else False
    elif not required:
        return default
    else:
        print(f"Value {key} not found in input")
        exit(1)


if __name__ == '__main__':
    main()
