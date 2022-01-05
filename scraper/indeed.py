"""
A web scraper that extract all jobs from indeed.com
"""

import re
import time
import json
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup

import utils


session = requests.Session()


class IndeedScraper:
    """Scrape Job posts from www.indeed.com."""

    def __init__(self, query, location=""):
        self.query = query
        self.location = location
        self.base_url = "https://www.indeed.com"
        self.url = f"{self.base_url}/jobs?q={self.query}&l={location}&limit=50"
        self.all_jobs = {}
        self.filename = ""

    def get_descriptions(self, job_keys):
        """Get job description of all jobs on a single page."""
        try:
            params = (("jks", ",".join(job_keys)),)
            r = session.get("https://www.indeed.com/rpc/jobdescs", params=params)
            if r.status_code == 200:
                return json.loads(r.content)
            else:
                print("(Retrying after 10 sec)...")
                time.sleep(10)
                r = session.get("https://www.indeed.com/rpc/jobdescs", params=params)
                return json.loads(r.content) if r.status_code == 200 else None
        except:
            print("It seems your Internet connection is slower. Try again later.")
            return None

    def get_similar_jobs(self, start_url):
        """Extract similar jobs in other locations starting from the given url."""

        print("Extracting similar jobs...")
        start_url += "&filter=0"
        current_page = self.extract_page(start_url)
        time.sleep(random.randint(5, 10))
        page = 1
        if current_page:
            while True:
                try:
                    next_page = current_page.find("a", {"aria-label": "Next"})
                    next_url = f"https://www.indeed.com{next_page.get('href')}"
                    current_page = self.extract_page(next_url)
                    page += 1
                    time.sleep(random.randint(5, 10))
                    if page % 4 == 0:
                        time.sleep(random.randint(60, 90))
                except AttributeError:
                    print("Finished.")
                    break
                except Exception as error:
                    print(f"Failed to extract similar jobs.", error)
        else:
            print("Failed to extract current page (similar).")

    def get_job_detail(self, job):
        """Extract job detail for a single job post."""

        company = job.find("span", class_="companyName").text.strip()
        title = job.find("h2", "jobTitle").contents[-1].text.strip()
        salary = "0"
        try:
            salary_con = job.find("div", class_="salary-snippet-container")
            if salary_con:
                salary = salary_con.find("div", class_="attribute_snippet").text.strip()
                salary = re.sub(
                    r"(\ba year|per|year|hour|an hour|hr|\/hr|a month\b)", "", salary
                )
        except:
            salary = "0"

        location = job.find("div", class_="companyLocation").text.strip()
        more_loc = job.find("span", class_="more_loc_container")
        if more_loc:
            more_loc_link = self.base_url + more_loc.find("a").attrs.get("href")
            self.get_similar_jobs(more_loc_link)
            return None

        location = re.sub(r"(\+\d+ location[s]?)", "", location)
        location = location.replace("•", " or ")
        if location.lower() == "remote":
            country = "Remote"
        else:
            country = self.location if self.location else "USA"
        remote = "Yes" if "remote" in location.lower() else "No"
        job_key = ""
        href = job.attrs.get("href")
        if "?jk=" in href:
            job_key = href.split("?")[-1].split("&")[0].split("=")[-1]
        elif "?fccid=" in href:
            job_key = href.split("?")[0].split("-")[-1]
        link = f"{self.base_url}/viewjob?jk={job_key}" if job_key else ""

        return (job_key, [company, title, salary, location, country, remote, link])

    def extract_page(self, url):
        """Extract details of jobs on a single page."""

        global session

        try:
            r = session.get(url)
            if r.status_code == 200:
                current_page = BeautifulSoup(r.content, "lxml")
                jobs = current_page.find_all("a", class_="tapItem")
                print("Jobs Found: ", len(jobs))

                for job in jobs:
                    if self.get_job_detail(job):
                        job_key, job_detail = self.get_job_detail(job)
                        self.all_jobs[job_key] = job_detail

                job_keys = list(self.all_jobs.keys())

                time.sleep(random.randint(5, 10))
                descriptions = self.get_descriptions(job_keys)

                if descriptions:
                    for job_key, job_detail in self.all_jobs.items():
                        job_desc = descriptions[job_key]
                        if job_desc:
                            job_desc = BeautifulSoup(job_desc, "lxml").find("body")
                            responsibility = utils.get_responsibility(job_desc)
                            qualification = utils.get_qualification(job_desc)
                            skills, experience = utils.get_skills_and_experience(
                                job_desc
                            )
                            expectations = f"{responsibility}\n{skills}"

                            more_detail = [expectations, qualification, experience]
                            new_job_detail = (
                                job_detail[:5] + more_detail + job_detail[5:]
                            )
                            self.all_jobs[job_key] = new_job_detail
                        else:
                            # failed to extract job description
                            new_job_detail = (
                                job_detail[:5]
                                + ["None", "None", "None"]
                                + job_detail[5:]
                            )
                            self.all_jobs[job_key] = new_job_detail
                else:
                    for job_key, job_detail in self.all_jobs.items():
                        new_job_detail = (
                            job_detail[:5] + ["None", "None", "None"] + job_detail[5:]
                        )
                        self.all_jobs[job_key] = new_job_detail

                utils.save_to_csv(self.all_jobs, self.filename)
                self.all_jobs = {}
                return current_page
            else:
                print("The server didn't respond with 200 Ok for current page.")
                return None
        except Exception as error:
            print("Failed to extract page.\n", error.with_traceback())
            return None

    def extract_all_pages(self):
        """Extract all result pages starting from the first page."""

        global session

        if utils.get_progress(2):
            # already saved file found, append to it
            page_num, filename = utils.get_progress(2)
        else:
            # save to a new file
            page_num = 1
            today = datetime.today().strftime("%Y-%m-%d")
            filename = f"{self.query}-job-list-indeed-{today}.csv"

        self.filename = filename

        print(f"Extracting jobs on page [ {page_num} ]...")
        start_url = f"{self.url}&start={(page_num-1)*50}"
        current_page = self.extract_page(start_url)
        time.sleep(random.randint(5, 10))

        if current_page:
            while True:
                try:
                    next_page = current_page.find("a", {"aria-label": "Next"})
                    next_url = f"https://www.indeed.com{next_page.get('href')}"
                    page_num += 1
                    print(f"Extracting jobs on page [ {page_num} ]...")
                    current_page = self.extract_page(next_url)

                    # Throttling the request to avoid being blocked by the server
                    time.sleep(random.randint(5, 10))
                    if page_num % 5 == 0:
                        time.sleep(random.randint(60, 90))

                    utils.save_progress(page_num + 1, self.filename, 2)
                except AttributeError:
                    print("\n\nFinished extracting all result pages.")
                    break
                except:
                    print(f"Failed to extract jobs on page {page_num}.")
                    break

        print(
            f"\nExtracted job listing is saved to Desktop with filename: {self.filename}\n"
        )
