"""Scrape job posts from indeed.com and dice.com """

import sys
import time

sys.path.append("scraper")  # used for importing modules inside scraper dir

from scraper import indeed, dice


def welcome():
    print("-" * 40)
    print("Welcome to Job scraper.")
    print("-" * 40)
    print("From which website you want to scrape?")
    print("\t1 - www.dice.com\n\t2 - www.indeed.com\n")
    ch = input("Your choice: ")

    if ch == "1" or ch == "2":
        return int(ch)
    else:
        print("Wrong choice. Exitting...")
        time.sleep(1)
        sys.exit(0)


def get_job_title():
    """Get the title of the job to search for."""
    query = input("Enter the job title: ")
    ch = input("Do you want to add location to your search? [Y/n]: ")
    if ch.lower() == "y":
        location = input("Enter location: ")
    else:
        location = ""

    return query, location


def main():
    start = time.time()

    choice = welcome()
    if choice == 1:
        query, location = get_job_title()
        scraper = dice.DiceScraper(query, location)
        print(f"Searching {query} jobs on www.dice.com ...\n")
        scraper.extract_all_pages()
    elif choice == 2:
        query, location = get_job_title()
        scraper = indeed.IndeedScraper(query, location)
        print(f"Searching {query} jobs on www.indeed.com ...\n")
        scraper.extract_all_pages()

    end = time.time()
    seconds = int(end - start)
    print(f"Total time taken: {seconds//60} min, {seconds%60} seconds")


if __name__ == "__main__":
    main()
