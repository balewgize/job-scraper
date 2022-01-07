"""
Utility functions used by indeed and dice scraper.
"""

import os
import re
import csv
import bs4


def get_home_dir():
    """Get the home directory of the user based the Operating System."""
    if os.name == "nt":
        return os.path.expanduser("~\\")
    else:
        return os.path.expanduser("~/")


def save_to_csv(job_list, filename):
    """Save a list of jobs to a CSV file."""
    home_dir = get_home_dir()
    if os.name == "nt":
        full_path = os.path.join(home_dir, "Desktop\\" + filename)
    else:
        full_path = os.path.join(home_dir, "Desktop/" + filename)

    mode = "a" if os.path.exists(full_path) else "w"
    with open(full_path, mode=mode, newline="", encoding="utf-8") as file:
        csv_writer = csv.writer(file)
        fields = (
            "Company",
            "Title",
            "Salary",
            "Location",
            "Country",
            "Expectations",
            "Qualifications",
            "Experience",
            "Remote",
            "Link",
        )
        if mode == "w":
            csv_writer.writerow(fields)  # write headers

        if type(job_list) == dict:
            csv_writer.writerows(list(job_list.values()))
        else:
            csv_writer.writerows(job_list)


def save_progress(page_num, filename, scraper):
    """Save scraping progress to avoid repeated extraction."""

    target = "dice" if scraper == 1 else "indeed"
    config_file = f".{target}_scraper_progress.txt"
    config_file_path = os.path.join(get_home_dir(), config_file)
    with open(config_file_path, "w") as file:
        file.write(f"{page_num},{filename}")


def get_progress(search_term, scraper):
    """Get the progress of scraper to continue where it left off."""

    target = "dice" if scraper == 1 else "indeed"
    config_file = f".{target}_scraper_progress.txt"
    home_dir = get_home_dir()
    config_path = os.path.join(home_dir, config_file)
    if os.path.exists(config_path):
        # read config file
        with open(config_path) as file:
            page_num, wanted_file = file.read().strip().split(",")

        # get fullpath to Desktop (based on Operating system)
        if os.name == "nt":
            desktop = os.path.join(home_dir, "Desktop\\")
        else:
            desktop = os.path.join(home_dir, "Desktop/")

        # searching wanted csv file in Desktop
        for root, dirs, files in os.walk(desktop):
            csv_files = [file for file in files if file.endswith(".csv")]
            for filename in csv_files:
                if filename == wanted_file and search_term in wanted_file:
                    return int(page_num), wanted_file

    return None


def clean_salary(salary):
    """Clean the salary given. Convert hourly rates to yearly and remove salary ranges."""
    salary = salary.strip()
    if "-" in salary:
        # it is expressed in range (take the higher)
        salary = salary.split("-")[-1].strip()

    # remove per year, annually, per hour, /hr etc.
    salary = re.sub(r"\.\d+", "", salary)
    salary = re.sub(r"\D", "", salary).strip()

    # convert hourly salary to yearly
    if re.search(r"(\d{2,3}$)", salary):
        match = re.search(r"(\d{2,3}$)", salary).group(0)
        hourly_salary = int(match)
        if hourly_salary > 200:
            # it may be weekly salary
            yearly_salary = hourly_salary * 4 * 12
        else:
            # it is hourly, convert it to yearly
            yearly_salary = hourly_salary * 9 * 5 * 4 * 12
        salary = str(yearly_salary)

    salary = f"${salary}"
    salary = re.sub(r"(\$\d?$)", "0", salary)
    return salary


def match_from_p_tag(all_p, pattern):
    """Search for a match to the pattern from the p tag."""
    match = set()
    for p in all_p:
        if re.search(pattern, p.text, re.IGNORECASE):
            match.add(p.text.strip())
    return "\n".join(match)


def match_from_text(all_p, pattern):
    """Search for a match to the pattern from the given text."""
    match = set()
    for p in all_p:
        if re.search(pattern, p, re.IGNORECASE):
            match.add(p.strip())
    return "\n".join(match)


def extract_from_sibling(all_p, pattern):
    """Extract required info that matches the pattern."""
    match = ""
    try:
        for p in all_p:
            words = p.text.strip().split(" ")
            if re.search(pattern, p.text.strip(), re.IGNORECASE) and len(words) < 10:
                sibling = p.next_sibling
                while (
                    sibling.text.strip() == "" and not type(sibling) == bs4.element.Tag
                ):
                    sibling = sibling.next_sibling
                if not sibling.find_all("li"):
                    match += sibling.text.strip() + "\n"
                else:
                    match += "\n".join(
                        [li.text.strip() for li in sibling.find_all("li")]
                    )
    except:
        pass

    return match


def get_responsibility(job_desc):
    """Extract responsibility associated with the job (if any)."""
    # a regex pattern used to search for responsibility
    pattern = r"\b(looking for|seeking|the role is|in this role|responsible|support|looking)\b"
    if type(job_desc) == bs4.element.Tag:
        responsibility = ""
        all_p = job_desc.find_all("p")

        # replace b tags by their text
        for p in all_p:
            [b.replace_with(b.text) for b in p.find_all("b")]

        if all_p:
            responsibility = match_from_p_tag(all_p, pattern)
        else:
            # the job description may be written as one paragraph separated by <br> tags
            b_tags = job_desc.find_all("b")
            unwanted = r"(requirements|qualification|responsibility|responsibilities)"
            for b_tag in b_tags:
                if re.search(unwanted, b_tag.text.strip(), re.IGNORECASE):
                    b_tag.decompose()  # remove b tags
                else:
                    b_tag.replace_with(b_tag.text)

            [br.replace_with("\n") for br in job_desc.find_all("br")]
            all_text = list(filter(None, job_desc.text.strip().split("\n")))
            responsibility = match_from_text(all_text, pattern)

        words = responsibility.strip().split(" ")
        if words and len(words) < 10:
            responsibility = ""
            pattern_two = (
                r"(\bDuties|Responsibility|Responsibilities|Roles|Requirements|Scope\b)"
            )
            responsibility = extract_from_sibling(all_p, pattern_two)
        # remove bullets (if any)
        responsibility = responsibility.replace("\xa0", "").replace("•", "").strip()
    else:
        all_text = job_desc.strip().split(". ")
        responsibility = match_from_text(all_text, pattern)
    return responsibility


def get_skills_and_experience(job_desc):
    """Extract skills and experience required for the job."""
    pattern = r"\b(experience|years|\+ years|yrs)\b"
    experience = set()
    skills = set()
    if type(job_desc) == bs4.element.Tag:
        all_li = job_desc.find_all("li")
        for li in all_li:
            text = li.text.strip()
            if re.search(pattern, text, re.IGNORECASE):
                experience.add(text)
                if not re.search(r"\d", text):
                    skills.add(text)

        all_p = job_desc.find_all("p")
        for p in all_p:
            [b.replace_with(b.text) for b in p.find_all("b")]

        if all_p and not experience:
            experience.add(match_from_p_tag(all_p, pattern))
        elif not experience:
            b_tags = job_desc.find_all("b")
            unwanted = r"(requirements|qualification|responsibility|responsibilities)"
            for b_tag in b_tags:
                if re.search(unwanted, b_tag.text.strip(), re.IGNORECASE):
                    b_tag.decompose()
                else:
                    b_tag.replace_with(b_tag.text)

            [br.replace_with("\n") for br in job_desc.find_all("br")]
            all_text = list(filter(None, job_desc.text.strip().split("\n")))
            experience.add(match_from_text(all_text, pattern))

        experience = "\n".join(experience)
        exp_words = experience.strip().split(" ")
        if exp_words and len(exp_words) < 10:
            # print("Bug 2 is here ")
            experience = ""
            experience = extract_from_sibling(all_p, r"(\bExperience\b)")

        skills = "\n".join(skills)
        skill_words = skills.strip().split(" ")
        if skill_words and len(skill_words) < 10:
            # print("Bug 3 is here ")
            skills = ""
            skills = extract_from_sibling(all_p, r"(\bSkills\b)")

        skills = skills.replace("\xa0", "").replace("•", "").strip()
        experience = experience.replace("\xa0", "").replace("•", "").strip()
    else:
        all_p = job_desc.strip().split(". ")
        experience = match_from_text(all_p, pattern)

    skills = experience if not skills else skills

    return skills, experience


def get_qualification(job_desc):
    """Extract qualification required for the job (if any)."""

    qualification = "NIL"  # default value
    pattern_one = (
        r"(\b(Bachelor(['|’]?s)?|BA\s?/\s?BS|BS\s?/\s?BA|BS[c]?|BA|"
        + r"Associate(['|’]s)?|Master(['|’]?s)?|MS[c]?) "
        + r"(degree|with \d\+ (years|yrs))? (in (?:(?!(or|\.|\s\s)).)*)?\b)"
    )
    pattern_two = (
        r"(\b(PhD|BS[c]?|MS[c]?) (in (?:(?!(or|\.|/|\s\s)).)*|with \d\+ years)?\b)"
    )

    if type(job_desc) == bs4.element.Tag:
        match_one = re.search(pattern_one, job_desc.text, re.IGNORECASE)
        match_two = re.search(pattern_two, job_desc.text, re.IGNORECASE)
    else:
        match_one = re.search(pattern_one, job_desc, re.IGNORECASE)
        match_two = re.search(pattern_two, job_desc, re.IGNORECASE)

    if match_one:
        qualification = match_one.group(0)
    elif match_two:
        qualification = match_two.group(0)
    return qualification
