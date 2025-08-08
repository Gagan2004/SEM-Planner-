# Project Setup: SEM Keyword Planner

This guide provides the necessary steps to configure and run the Python script for generating a keyword plan.

---

## 1. Setup Instructions

Follow these three steps to prepare the project.

### Step 1.1: Install Dependencies

This step installs the necessary Python libraries from the `requirements.txt` file.

1.  Open your terminal in the project folder.
2.  Run the following command:
    ```bash
    pip install -r requirements.txt
    ```

### Step 1.2: Configure Google Ads API Credentials

This step securely connects the script to your Google Ads account.

1.  Open the `google-ads.yaml` file.
2.  Fill in your unique credentials:
    * `developer_token`
    * `login_customer_id` (Your MCC ID)
    * `client_id` & `client_secret`
    * `refresh_token`

### Step 1.3: Configure Project & AI Inputs

This file dictates which brand the script will analyze.

1.  Open the `config.yaml` file.
2.  Fill in the required project details:
    * `google_ads_customer_id` (Your Account ID)

---

## 2. Running the Script

Once the setup is complete, run the tool with this single command in your terminal:

```bash
python keyword_tool.py
