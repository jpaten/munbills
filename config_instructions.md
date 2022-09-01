### Configuration instructions
In order to use MUNBills, you will have to fill out every element of this config file with your
Stripe keys and details regarding your conference's registration system.  It's easiest to do this by making a copy of the
sample_config.json file, then filling in each element based on the details below. **If you're contributing to MUNBills make sure
never to add your config or any other file containing your Stripe keys to Git**.
If anything is unclear, please let me know by creating an issue or emailing Jonah at [finance@bruinmun.org](mailto:finance@bruinmun.org)

### Details

 - `key_type`: The name of the config, for example TEST or LIVE,
 - `api_key`: Your Stripe API Key
 - `card_fee`: Stripe tax code for a card fee to be applied to all card payments, leave blank if there isn't one
 - `delegation_fee`: Stripe price code for delegation fee
 - `online_fees`
   - `E`: `Stripe price id for online early, leave an empty string if you will not have an online option
   - `R`: Stripe price id for online regular, leave an empty string if you will not have an online option
   - `L`: `Stripe price id for online late, leave an empty string if you will not have an online option
 - `ip_fees`
   - `E`: Stripe price id for in person early, leave an empty string if you will not have an in person option
   - `R`: Stripe price id for in person regular, leave an empty string if you will not have an in person option
   - `L`: Stripe price id for in person early, leave an empty string if you will not have an in person option
 - `EIN`: Stripe tax ID code for your EIN or tax id
 - `T1_coupon`: Stripe code for a coupon id you may apply for delegates. Leave an empty string if you do not need this
 - `finance_email`: Email for the Director of Finance, will be the sender of all invoices
 - `external_email`: Email for the Director of External, will be cc-ed on all emails. Can be left blank
 - `check_email`: A file path to a .html file used for check payment invoice emails
 - `card_email`: A file path to a .html file for card payment emails
 - `email_subject`: The subject line to be used for all drafts
 - `registration_start`: Array for the date when registration starts, of the form `[YYYY, MM, DD]`
 - `default_time`: The default number of days from when an invoice is created to when it is due
 - `input`
   - `delegation_name`: Position of delegation name in your registration sheet
   - `discount`: Position of the discount cell, should be 0 or 1 for true or false. Enter -1 here -1 if not applicable,
   - `no_delegation_fee`: Position of the discount cell, should be 0 or 1 for true or false. Enter -1 here -1 if not applicable
   - `head_del_name`: Position of the name of the head delegate / advisor which will appear on invoice.
   - `billing_address`: Position of the billing address, which must match card used for payment,
   - `email`: Position of orimary head del email, will appear on invoices and will be used for email drafts
   - `phone`: Position of the phone number to appear on invoices. This is a placeholder and is not yet implemented, leave as -1 for now.
   - `registration_period`: The position of the registration period, must be either `E`, `R`, or `L` for early, regular, or late registration, respectively.
   - `registration_date`: The position of the registration date.
   - `in_person_delegate_count`: The position of the number of in person delegates. This field is optional if there is no in person component to your conference, enter -1 instead
   - `online_delegate_count`: The position of the number of online delegates. This field is optional if there is no online component to your conference, enter -1 instead
   - `card`: Position of the payment method cell. Must be either "Credit Card" or "Check" in the spreadsheet.
   - `expected_cost`: Position of the expected cost for the delegation, used to confirm that the invoice is finalized correctly
   - `deadline`: Position of the deadline cell, which should be of the format MM/DD/YY or MM/DD/YYYY. If you do not have store deadlines in your sheet, enter -1 instead.
   - `days_left`: Position of the cell containing the number of days left. If you do not have such a cell, enter -1 here instead.
