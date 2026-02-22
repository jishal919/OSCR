# Charity Email Finder Automation Tool

A robust web automation system that extracts official charity websites from the OSCR register and intelligently crawls those websites to discover valid contact email addresses.

This tool is designed for reliability, resume capability, structured output generation, intelligent failure handling, and execution time monitoring.

---

# Overview

This automation system performs the following workflow:

1. Reads charity names from a CSV dataset.
2. Searches each charity on the OSCR register website.
3. Extracts the official website URL (if available).
4. Crawls the charity’s website intelligently.
5. Extracts and validates contact email addresses.
6. Saves structured results incrementally.
7. Automatically resumes from the last processed entry.
8. Measures and prints execution time statistics.

---

# Core Features

## Intelligent Website Handling

- Skips HTTP 404 and server errors immediately.
- Skips expired or non-existent domains (DNS NXDOMAIN).
- Skips slow or unresponsive websites.
- Retries only when full internet disconnection is detected.
- Prevents unnecessary retry loops on broken websites.

## Smart Email Extraction

- Regex-based extraction from page HTML.
- Strict email cleaning and validation.
- TLD validation.
- Rejects file-type extensions (png, jpg, css, js, pdf, etc.).
- Rejects malformed or image-dimension domains.
- Prefers generic organizational emails:
  - info@
  - contact@
  - enquiries@
  - admin@
  - hello@
  - office@
  - support@
  - team@

## Controlled Domain Crawling

- Starts from the homepage.
- Automatically checks common paths:
  - /contact
  - /contact-us
  - /about
  - /team
- Crawls only internal domain links.
- Stops immediately once a valid email is found.
- Crawl depth is limited for performance control.

## Resume & Crash Safety

- Uses an `Index` column in the output CSV.
- Automatically detects the last processed charity.
- Continues from `last_index + 1`.
- Prevents duplicate entries.
- Saves progress after each charity.

## Performance Monitoring

For each processed charity:

- Prints execution time in seconds.
- Maintains a rolling average execution time.
- Helps estimate total dataset processing time.

Example output:

Execution Time: 6.42 sec  
Average Time: 5.87 sec  

Timing begins when visiting the OSCR search page and ends after email extraction or crawl completion.

---

# Project Structure
project/
│
├── TrusteeConnect Data.csv # Input dataset
├── charity_results.csv # Output file (auto-generated)
├── main.py # Main automation script
├── report_emails_found.csv # Sample Report
└── README.md #documentation



---

# Input Requirements

The input CSV must contain a column named exactly:

Charity Name

Example:

| Charity Name        |
|---------------------|
| Example Charity A   |
| Example Charity B   |

Encoding used for reading:

cp1252

---

# Output Format

The script generates:

charity_results.csv

Columns:

| Index | Charity Name | Website Status | Website URL | Contact Email Status | Contact Email |

Example:

| 15 | Example Charity | Found | https://example.org | Found | info@example.org |

Website Status:
- Found
- Not Found

Contact Email Status:
- Found
- Not Found

---

# Installation

## 1. Install Python

Python 3.9 or newer recommended.

## 2. Install Dependencies
pip install pandas playwright

## 3. Install Playwright Browsers
playwright install


---

# Technical Workflow

## Step 1 – Extract Charity Names

- Reads CSV using pandas.
- Cleans whitespace.
- Returns list of charity names.

## Step 2 – Search OSCR Register

- Navigates to:
  https://www.oscr.org.uk/search/register-search
- Submits charity name.
- Extracts official website URL if available.

## Step 3 – Crawl Website

- Visits homepage.
- Visits common contact paths.
- Crawls internal links only.
- Extracts raw HTML.
- Searches for valid email patterns.

## Step 4 – Email Validation Rules

Each email must:

- Match regex pattern.
- Have TLD length ≥ 2.
- Contain alphabetic characters in domain.
- Not resemble file extensions.
- Have local-part length ≤ 64 characters.

Preferred generic addresses are selected first.

## Step 5 – Save Results

- Results appended immediately.
- Duplicate charity entries are prevented.
- Resume functionality remains intact even after interruption.

---

# Error Handling Logic

The system differentiates between:

## Internet Disconnection
- Detects `net::err_internet_disconnected`
- Retries until connection returns.

## DNS Failure (NXDOMAIN)
- Skipped immediately.
- No retry.

## HTTP Errors (404, 500)
- Skipped immediately.

## Slow or Hanging Pages
- Timeout after 15 seconds.
- Skipped automatically.

---

# Execution Timing Logic

Execution time per charity includes:

- Opening OSCR search page.
- Performing search.
- Extracting website.
- Crawling website.
- Email extraction process.

A rolling average is maintained:

Average Time = Total Execution Time / Number of Processed Charities

This provides real-time performance insight during large dataset processing.

---

# Design Principles

- Deterministic processing.
- Controlled crawl depth.
- Minimal retry loops.
- Fail-fast behavior for invalid domains.
- Resume-safe execution.
- Immediate result persistence.
- Structured and clean CSV output.

---

# Summary

This automation tool provides:

- Structured charity data enrichment.
- Intelligent website crawling.
- Clean and validated email discovery.
- Crash-safe resume capability.
- Smart failure detection.
- Performance tracking with rolling average timing.

It is designed for reliability, scalability, and structured data collection workflows.