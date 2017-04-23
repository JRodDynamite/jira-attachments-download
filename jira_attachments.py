import os
import re
import requests


from bs4 import BeautifulSoup
from jira import JIRA
from requests.auth import HTTPBasicAuth


## ***CONFIGURATIONS*** Begin
JIRA_SERVER = "" #without slash at the end
JIRA_USERNAME = ""
JIRA_PASSWORD = ""
JQL = ''

## Regex to match filetype to download
## If "", all attachments of the issue will be downloaded
ATTACHMENT_RE = "\.docx{0,1}$"

## Provide download location
## If "", files will be created where this script located
DOWNLOAD_LOCATION = "D:/temp/" #with slash at the end
## ***CONFIGURATIONS*** End


if not os.path.exists(DOWNLOAD_LOCATION):
    os.makedirs(DOWNLOAD_LOCATION)


options = {
    'server' : JIRA_SERVER,
    'basic_auth' : (JIRA_USERNAME, JIRA_PASSWORD)
}
jira_inst = JIRA(**options)


def download_file(url_data):
    local_filename = url_data[0]
    # NOTE the stream=True parameter
    r = requests.get(url_data[1], auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD), stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                #f.flush() commented by recommendation from J.F.Sebastian
    return local_filename


def fetch_jql_issues(startsAt):
    issues = jira_inst.search_issues(JQL, startsAt)
    return issues


def create_folder(issue):
    if not os.path.exists(DOWNLOAD_LOCATION + issue):
        os.makedirs(DOWNLOAD_LOCATION + issue)


def parse_response(resp, issue):
    soup = BeautifulSoup(resp.text, 'html.parser')
    attachments = soup.select("ol#file_attachments .attachment-title a[href^='/secure/attachment']")
    if len(attachments) == 0:
        print "No attachments with matching regex"
        return
    for att in attachments:
        att_url = att.attrs['href']
        if ATTACHMENT_RE == "" or re.search(ATTACHMENT_RE, att_url):
            create_folder(issue)
            path = DOWNLOAD_LOCATION + issue + "/" + att.text.strip()
            download_file([path, JIRA_SERVER + att_url])
            print att.text.strip() + " Download successful"


def fetch_issues_from_jql(issues):
    issues_list = [issue.key for issue in issues]
    for issue in issues_list:
        print "***" + issue + "***" + " - Downloading attachments"
        if os.path.exists(DOWNLOAD_LOCATION + issue):
            print "Attachments downloaded. Folder exist."
        else:
            resp = requests.get(JIRA_SERVER + '/issues/' + issue,
                                auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD))
            if resp.status_code == 200:
                parse_response(resp, issue)
            
        print "***" + issue + "*** - Downloading Done"
        print "\n"


if __name__ == "__main__":
    issues_fetched = 0
    issues = jira_inst.search_issues(JQL, 0)
    print "For the JQL - " + JQL
    total_issues = issues.total
    print "Total number of issues: " + str(total_issues)
    total_issues = 2
    cont = raw_input("Continue? (y/n)")
    if cont.lower() == "y":
        while issues_fetched < total_issues:
            issues = jira_inst.search_issues(JQL, issues_fetched)
            issues_fetched += len(issues)
            fetch_issues_from_jql(issues)
