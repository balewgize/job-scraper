# Job Scraper

Scrape all job posts appearing on a search result from www.indeed.com and www.dice.com.

It was built for <a href="https://www.upwork.com">Upwork</a> client that needs all job listings
and their details extracted.

Features:

- fast
- robust (exception handling)
- pagination (scrape all result pages)
- resume capability (continue where it left off incase of failure)

## How to use

- Open Terminal or Cmd and go to the directory you want to put these project files.
  Then clone the repository and navigate to job-scraper dir

```
git clone https://github.com/balewgize/job-scraper.git
```

```
cd job-scraper/
```

- Create a virtual environment inside job-scraper directory

```
python -m venv venv
```

- Activate the virtual environment
  (For Windows user)

```
.\venv\Scripts\activate
```

(For Linux and Mac)

```
source venv/bin/activate
```

- Install required packages

```
pip install -r requirements.txt
```

- Finally run the scraper

```
python job-scraper.py
```

## Sample data

![Alt text](/screenshot/sample-data.png?raw=true "Screenshot")

Thanks
