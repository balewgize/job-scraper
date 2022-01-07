"""
A web scraper that extracts all jobs from dice.com
"""

import re
import json
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import concurrent.futures

import utils


session = requests.Session()


class DiceScraper:
    """
    Scrape job posts from www.dice.com based on given keyword and return
    details about the jobs.
    """

    def __init__(self, query, location=""):
        self.query = query
        self.all_jobs = []
        self.filename = ""
        self.base_url = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

        # this are obtanied from the cURL request the browser is making to the server
        # We need it to be able to search for jobs using different keywords,
        # to extract all result pages starting from the first page, and
        # to limit how many jobs we want in one page (pageSize)

        self.headers = {
            "authority": "job-search-api.svc.dhigroupinc.com",
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
            "accept": "application/json, text/plain, */*",
            "sec-ch-ua-mobile": "?1",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
            "x-api-key": "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",
            "sec-ch-ua-platform": '"Android"',
            "origin": "https://www.dice.com",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.dice.com/",
            "accept-language": "en-US,en;q=0.9",
        }

    def get_params(self, page_num):
        """Return parameters to be used to search for jobs."""
        params = (
            ("q", self.query),
            ("page", page_num),
            ("pageSize", "100"),
            (
                "facets",
                "employmentType|postedDate|workFromHomeAvailability|employerType|easyApply|isRemote",
            ),
            ("filters.employmentType", "FULLTIME|PARTTIME|CONTRACTS|THIRD_PARTY"),
            (
                "fields",
                "id|jobId|summary|title|postedDate|modifiedDate|jobLocation.displayName|detailsPageUrl|salary|clientBrandId|companyPageUrl|companyLogoUrl|positionId|companyName|employmentType|isHighlighted|score|easyApply|employerType|workFromHomeAvailability|isRemote",
            ),
            ("interactionId", "1"),
            ("fj", "true"),
            ("includeRemote", "true"),
            ("eid", "a6zd7NUgR0Wy8Tzf36TS2Q_|Sh_4hXkUSsuaDyYXXmPLAQ_2"),
        )
        return params

    def get_salary(self, job, job_desc):
        """Extract salary information for the job posting (if any)."""
        pattern = r"(\$\d{2,}([,|.]?\d*|[k|K])\s?((-|to)\s?\$\d{2,}([,|.]?\d*|[k|K]))?)"
        salary = "0"
        try:
            salary = job["salary"]
            if not re.search(r"\d+", salary):
                # the salary is expressed with words like 'Based on Experience'
                # and salary may be in the job title, or in the job description
                salary = "0"
        except KeyError:
            salary = "0"
        finally:
            if salary == "0":
                if re.search(pattern, job["title"]):
                    salary = re.search(pattern, job["title"]).group(0)
                elif re.search(pattern, job_desc.text):
                    salary = re.search(pattern, job_desc.text).group(0)

        salary = salary.strip().lower()
        salary = salary.replace("k", ",000")
        salary = salary.replace("to", "-")
        if not salary.startswith("$") and salary != "0":
            salary = "$" + salary

        salary = utils.clean_salary(salary)
        return salary

    def is_remote_job(self, job, job_desc):
        """Checks if the job is remote or not."""
        # words that recruiters use to describe remote jobs
        pattern = r"\bWFH|100% remote|100% Remote/WFH|100% Remote / WFH|100% WFH|100% WFH/Remote|100% WFH / Remote\b"

        if job["isRemote"]:
            return "Yes"
        else:
            if re.search(pattern, job_desc.text, re.IGNORECASE):
                return "Yes"
            if re.search(pattern, job["title"]):
                return "Yes"
        return "No"

    def get_job_location(self, job):
        """Return address of the job (location and country)"""
        try:
            adress = job["jobLocation"]["displayName"].split(",")
            location = f"{adress[0]}, {adress[1]}"
            country = adress[-1]
        except KeyError:
            location = ""
            country = ""

        if job["isRemote"] and location != "":
            location = "Remote or " + location
        elif job["isRemote"] and location == "":
            location = "Remote"

        if job["isRemote"] and country == "":
            country = "Remote"

        return (location, country)

    def get_job_description(self, job, timeout):
        """Extract description of a job."""
        job_link = job["detailsPageUrl"]
        time.sleep(2)
        r = requests.get(job_link, headers=self.headers, timeout=timeout)

        if r.status_code == 200:
            # extract responsibility, skills_required ... from job description
            html = BeautifulSoup(r.content, "lxml")
            job_description = html.find("div", id="jobdescSec")
            return job_description
        else:
            # failed to extract description of the job, use the job summary
            return job["summary"]

    def extract_job_detail(self, job, timeout):
        """Extract job description and other details for a job."""
        company = job["companyName"]
        title = job["title"]
        link = job["detailsPageUrl"]
        location, country = self.get_job_location(job)

        job_desc = self.get_job_description(job, timeout)

        responsibility = utils.get_responsibility(job_desc)
        qualification = utils.get_qualification(job_desc)
        skills, experience = utils.get_skills_and_experience(job_desc)
        expectations = f"{responsibility}\n{skills}"

        remote = self.is_remote_job(job, job_desc)
        salary = self.get_salary(job, job_desc)

        return (
            company,
            title,
            salary,
            location,
            country,
            expectations,
            qualification,
            experience,
            remote,
            link,
        )

    def extract_page(self, page_num):
        """Extract job details from a single search result page."""
        global session

        params = self.get_params(page_num)
        time.sleep(2)
        r = session.get(self.base_url, headers=self.headers, params=params)
        if r.status_code == 200:
            result = json.loads(r.content)
            jobs = result["data"]
            print("Extracting jobs on page (", page_num, ")...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_job = {
                    executor.submit(self.extract_job_detail, job, 120): job
                    for job in jobs
                }
                for future in concurrent.futures.as_completed(future_to_job):
                    try:
                        job_detail = future.result()
                    except:
                        pass
                    else:
                        self.all_jobs.append(job_detail)

            utils.save_to_csv(self.all_jobs, self.filename)
            self.all_jobs = []

    def extract_all_pages(self):
        """Extract all result pages for a certain keyword."""
        global session

        if utils.get_progress(self.query, 1):
            # already saved file found, append to it
            current_page, filename = utils.get_progress(self.query, 1)
        else:
            # save to a new file
            current_page = 1
            today = datetime.today().strftime("%Y-%m-%d")
            filename = f"{self.query}-job-list-dice-{today}.csv"

        self.filename = filename
        params = self.get_params(current_page)
        r = session.get(self.base_url, headers=self.headers, params=params)

        if r.status_code == 200:
            result = json.loads(r.content)
            jobs = result["data"]
            page_count = result["meta"]["pageCount"]
            print(f"Total pages to be scraped: {page_count} ( around 100 jobs in each)")
            print("\nExtracting jobs on page (", current_page, ")...")

            # extract the first page and paginate to other pages
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_job = {
                    executor.submit(self.extract_job_detail, job, 120): job
                    for job in jobs
                }
                for future in concurrent.futures.as_completed(future_to_job):
                    try:
                        job_detail = future.result()
                    except:
                        pass
                    else:
                        self.all_jobs.append(job_detail)

            utils.save_progress(current_page + 1, self.filename, 1)

            while current_page <= page_count:
                current_page += 1  # go to the next page
                self.extract_page(current_page)
                utils.save_progress(current_page + 1, self.filename, 1)

                if current_page % 10 == 0:
                    # wait some seconds to avoid overwhelming the server
                    time.sleep(random.randint(20, 60))

                time.sleep(random.randint(10, 20))
        else:
            print("Error occurred while searching. Try again.")

        print(
            f"\nExtracted job listing is saved to Desktop with filename: {self.filename}\n"
        )
