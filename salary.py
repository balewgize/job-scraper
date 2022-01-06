import re

def clean_salary(salary):
    """Clean the salary given. Conver hourly rates to yearly and remove salary ranges."""
    if "-" in salary:
        # it is expressed in range (take the higher)
        salary = salary.split("-")[-1].strip()
    if not salary.startswith("$"):
        salary = "$" + salary.strip()
    
    # remove per year, annually, per hour, /hr etc.
    salary = re.sub(r"([a-zA-Z\/\+])", "", salary)
    salary = re.sub(r"\.\d+", "", salary)
    salary = re.sub(r"\$+", "$", salary)
    salary = salary.strip()

    # convert hourly salary to yearly
    if re.search(r"(\$[0-9]{2,3}$)", salary):
        match = re.search(r"(\$\d{2,3}$)", salary).group(0)
        hourly_salary = int(match[1:])
        yearly_salary = hourly_salary * 9 * 5 * 4 * 12
        salary = "$" + str(yearly_salary)
    if salary in ['$', "$0"]:
        salary = "0"
    print(salary)
    return salary

s = "$140,000+"
clean_salary(s)