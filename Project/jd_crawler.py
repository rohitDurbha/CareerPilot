import requests
from bs4 import BeautifulSoup

def parse_linkedin_job(job_url):
    headers = {
        # Use your real LinkedIn cookies for authenticated access, if needed
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }
    response = requests.get(job_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(soup.prettify())  # For debugging: print the entire HTML content
    # Extract job details
    job_data = {}
    job_data['title'] = soup.find('h1', class_="top-card-layout__title")
    if job_data['title']:
        job_data['title'] = job_data['title'].get_text(strip=True)

    job_data['company'] = soup.find('a', class_="topcard__org-name-link")
    if job_data['company']:
        job_data['company'] = job_data['company'].get_text(strip=True)

    job_data['location'] = soup.find('span', class_="topcard__flavor topcard__flavor--bullet")
    if job_data['location']:
        job_data['location'] = job_data['location'].get_text(strip=True)

    job_data['description'] = soup.find('div', class_="show-more-less-html__markup")
    if job_data['description']:
        job_data['description'] = job_data['description'].get_text(separator="\n", strip=True)

    return job_data

# Example usage:
job_url = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4312198283"  # Replace with real job URL
parsed_job = parse_linkedin_job(job_url)
print(parsed_job)
