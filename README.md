# MunBills!
Hi! MunBills is a simple Python program to make Stripe invoices for MUN conferences, supporting sending personalized emails and configuration for different registration formats!
## Advantages
 - Create invoices and send out emails in less than three minutes(we timed it!)]
 - Easily enter data just by copying a row from your registration spreadsheet!
 - Configure everything to match your conference needs!
 ## Quickstart Guide
 0. Make sure you have Python 3.10 installed on your system.
 1. Install the [Python Stripe library](https://stripe.com/docs/development/quickstart/python) and [Gmail API](https://developers.google.com/gmail/api/quickstart/python), and follow their quickstart guides to ensure everything is set up properly. You will need to create a new project to use the Gmail API and obtain both a gmail API key and oauth config, which will need to be setup either as a development version or an internal project.
 2. Setup Stripe products for a delegation fee, and per-delegate fees, including an early, regular, and late registration fee for per-delegate fees(only one price may be used for delegation fees at this time). Then, referencing these keys and your registration form, create a copy of [`sample_config.json`](/sample_config.json) and complete it following the [configuration guide](/config_instructions.md/).
 3. Change the line beginning `CONFIG_FILE = ` to be a path to your completed config. We highly recommend that you place this in a folder not under version control to avoid any possibility that you make your Stripe keys public.
 3. Download your Gmail API authorization credentials, and place them in the main folder. Ensure that they are not committed ever!
 4. Run the program with `python3 invoicerator.py`, then follow the instruction prompts!
