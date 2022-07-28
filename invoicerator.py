import string
import stripe
import datetime
import requests

#Placeholders for Github
stripe.api_key = "nope"
CARD_FEE = "nope"
DELEGATION_FEE = "nope"
ONLINE_DEL_FEE = {"E": "nope", "R": "nope",
                  "L": "nope"}
IP_DEL_FEE = {"E": "nope", "R": "nope",
              "L": "nope"}
EIN = "nope"
T1_COUPON = "nope"


DAYS_LEFT = 30
REGISTRATION_START = datetime.datetime(2022, 6, 1)

from_american = lambda date: datetime.datetime(int(date[2]), int(date[0]), int(date[1]))

def main():
    line = input()
    lineList = line.split("\t")
    print(lineList)
    school = lineList[0]
    t1 = True if lineList[1] == "1" else False
    ind = True if lineList[2] == "1" else False
    advName = lineList[3]
    address = lineList[4]
    email = lineList[5]
    period = lineList[6]
    regDate = lineList[7]
    ipDels = int(lineList[8])
    olDels = int(lineList[9])
    card = True if lineList[13] == "Credit Card" else False
    amountToInvoice = lineList[15]
    deadline = lineList[17]
    daysLeft = lineList[18]

    # Create or retrieve Customer
    # First extract address
    input(f"Address given as {address}, is this correct?")
    address_fix = address.replace(", ", ",")
    address_split = address_fix.split(",")
    street_address = string.capwords(address_split[0])  # TODO: line 2
    line_two = input("Enter address line two or press enter")
    if line_two:
        street_address = input("Enter address line one")
    address_city = string.capwords(address_split[1])
    address_rest = address_split[2].split()
    print(address_rest)
    address_state = string.capwords(address_rest[0])  # TODO: validation
    try:
        address_zip = int(address_rest[1].split("-")[0]) #TODO: addresses with dashes
        address_country = " ".join(address_rest[2:])
    except ValueError:
        address_state = string.capwords(address_rest[0] + " " + address_rest[1])
        address_zip = address_rest[2]
        address_country = " ".join(address_rest[3:])
    if address_country.lower() in ["us", "united states", "united states of america", "usa"]:
        address_country = "US"
    else:
        address_country = input("Country not detectable, enter 2 letter code")
    if address_state.lower() in ["california", "ca"]:
        address_state = "California"
    else:
        new_state = input(
            F"Address state given as {address_state}. Enter new state(full) or press return to use entered state")
        if new_state not in string.whitespace:
            address_state = new_state
    if line_two:
        cust_address = {"city": address_city, "country": address_country, "state": address_state,
                        "line1": street_address, "line2": line_two, "postal_code": address_zip}
    else:
        cust_address = {"city": address_city, "country": address_country, "state": address_state,
                        "line1": street_address, "postal_code": address_zip}

    # Check for existing customer
    found_customers = stripe.Customer.search(query=f"name~ '{advName}' AND email: '{email}'")
    if found_customers["data"]:
        if len(found_customers["data"]) > 1:
            for i in range(len(found_customers["data"])):
                made_date = datetime.date.fromtimestamp(found_customers["data"][i].created)
                print(f"Customer {i}, generated on {made_date.year}-{made_date.month}-{made_date.day}:\n {found_customers['data'][i]}")
            while True:
                customer_number = input("Many customers found, please type the number of the customer to use")
                try:
                    customer = found_customers["data"][int(customer_number)]
                    break
                except ValueError:
                      print("Input was not a number, try again")
                except IndexError:
                    print("Not a valid customer, try again")
            to_delete = input("Delete other customers? (Y/n)")
            if to_delete == "Y":
                for i in range(len(found_customers["data"])):
                    if i != int(customer_number):
                        stripe.Customer.delete(found_customers["data"][i].id)
        else:
            customer = found_customers["data"][0]
        customer = stripe.Customer.modify(
            customer.id,
            shipping={"address": {}, "name": {}, "phone": {}},
            address=cust_address,
            description=school)

    else:
        customer = stripe.Customer.create(
            description=school,
            email=email,
            name=advName,
            address=cust_address
        )

    # Invoice is already paid, so get a receipt
    if daysLeft == "PAID":
        # Check it was actually paid
        split_reg_date = regDate.split("/")
        if len(split_reg_date) == 3:
            datetime_reg_date = from_american(split_reg_date)
        else:
            print("Date not formatted properly")
            exit(1)
        paid_charges = stripe.Charge.search(query=f"customer: '{customer.id}' AND status: 'succeeded' AND created > '{int(datetime_reg_date.timestamp())}'") #TODO: This doesn't work
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
    open_customer_payments = stripe.PaymentIntent.search(query=f"customer: '{customer.id}' AND status: 'requires_payment_method'", limit=99)
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
        decision = input(f"""Customer has at least {len(open_customer_payments['data'])} invoices. This might be bad! Please select an option:
        (C)ontinue as usual, creating another invoice or (Q)uit and review invoices on Stripe""")
        if decision == "Q":
            exit(0)

    # Delegation Fee
    if ind and ipDels + olDels > 1:
        input("WARNING: multiple delegates registered to an independent delegation, press enter to confirm, or quit")
    elif not ind:
        stripe.InvoiceItem.create(
            customer=customer,
            price=DELEGATION_FEE
        )

    # Per delegate fees
    if ipDels > 0:
        stripe.InvoiceItem.create(
            quantity=ipDels,
            customer=customer,
            price=IP_DEL_FEE[period]  # TODO: add validation
        )
    if olDels > 0:
        stripe.InvoiceItem.create(
            quantity=olDels,
            customer=customer,
            price=ONLINE_DEL_FEE[period]  # TODO: Validation
        )

    # Set due date
    days_left = 30
    if deadline != "":
        deadline_split = deadline.split("/")
        deadline_date = datetime.date(int(deadline_split[2]), int(deadline_split[0]), int(deadline_split[1]))
        days_left = (deadline_date - datetime.date.today()).days
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
    if float(invoice["total"]) / 100 != float(amountToInvoice[1:].replace(",","")):
        input(
            f"WARNING: Invoice for ${float(invoice['total']) / 100}, sheet calculated as ${amountToInvoice}, press enter to finalize or quit")
    else:
        input(
            f"Press enter to finalize invoice of {ipDels} IP dels & {olDels} OL dels for ${float(invoice['total']) / 100}")
    invoice = stripe.Invoice.finalize_invoice(invoice, auto_advance=False)
    print(invoice)

    # Download invoice
    r = requests.get(invoice.invoice_pdf)
    with open(f"./GeneratedInvoices/{invoice['number']}.pdf", "wb") as file:
        file.write(r.content)
    print(f"link: {invoice.hosted_invoice_url}, ")
    with open("./GeneratedInvoices/links.txt", "a") as file:
        file.write(f"{invoice.number} — {customer.description}: {invoice.hosted_invoice_url}\n")

    lineList[14] = "$" + str(float(invoice["total"]) / 100)
    today = datetime.date.today()
    lineList[11] = f"{today.month}/{today.day}/{today.year}"
    print("\t".join(lineList[10:14]))  # TODO: this doesn't work for some reason?


if __name__ == '__main__':
    main()
