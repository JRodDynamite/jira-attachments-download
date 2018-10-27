from datetime import datetime
import logging
import os
import re

from bs4 import BeautifulSoup
from jira import JIRA
import requests
from requests.auth import HTTPBasicAuth

## **************************
## CONFIGURATIONS Begin
## **************************

## Add base URL to JIRA server
## End it without slash
JIRA_SERVER = ""
JIRA_USERNAME = ""
JIRA_PASSWORD = ""
JQL = ''

## Regex to match filetype to download
## If "", all attachments of the issue will be downloaded
## Eg: "\.csv$", "\.msg$"
ATTACHMENT_RE = "\.docx{0,1}$"

## Provide download location
## If "", files will be created where this script located
## Use forward slash to show path. 
## Always end with a slash. Eg: "D:/temp/", "/home/user/Downloads/"
DOWNLOAD_LOCATION = "D:/temp/"

## ************************
## CONFIGURATIONS End
## ************************


if not os.path.exists(DOWNLOAD_LOCATION):
    os.makedirs(DOWNLOAD_LOCATION)


options = {
    'server' : JIRA_SERVER,
    'basic_auth' : (JIRA_USERNAME, JIRA_PASSWORD)
}
jira_inst = JIRA(**options)


def init_logging():
    '''function to initialize logging'''
    log_filename = "log_" + str(datetime.now()).split(".")[0].replace(":", "") + ".txt"
    logging.basicConfig(filename=DOWNLOAD_LOCATION + log_filename,
                        level=logging.INFO,
                        format='%(asctime)s : %(levelname)s : %(message)s',
                        datefmt='%d/%m/%Y %I:%M:%S %p')


def download_file(url_data):
    '''function to download the file from given url'''
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
    '''function to fetch issues using jql'''
    issues = jira_inst.search_issues(JQL, startsAt)
    return issues


def create_folder(issue):
    if not os.path.exists(DOWNLOAD_LOCATION + issue):
        os.makedirs(DOWNLOAD_LOCATION + issue)


def parse_response(resp, issue):
    soup = BeautifulSoup(resp.text, 'html.parser')
    attachments = soup.select("ol#file_attachments .attachment-title a[href^='/secure/attachment']")
    if len(attachments) == 0:
        log_and_print("No attachments in this issue.")
        return
    atleast_one_download = False
    for att in attachments:
        att_url = att.attrs['href']
        if ATTACHMENT_RE == "" or re.search(ATTACHMENT_RE, att_url):
            create_folder(issue)
            path = DOWNLOAD_LOCATION + issue + "/" + att.text.strip()
            download_file([path, JIRA_SERVER + att_url])
            atleast_one_download = True
            log_and_print(att.text.strip() + " Download successful")
    if not atleast_one_download:
        log_and_print("No attachments in this issue which match the regex.")


def fetch_issues_from_jql(issues):
    global issues_fetched
    issues_list = [issue.key for issue in issues]
    for issue in issues_list:
        log_and_print("***" + issue + "***" + " - Downloading attachments")
        issues_fetched += 1
        if os.path.exists(DOWNLOAD_LOCATION + issue):
            log_and_print("Attachments downloaded. Folder exist.")
        else:
            resp = requests.get(JIRA_SERVER + '/issues/' + issue,
                                auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD))
            if resp.status_code == 200:
                parse_response(resp, issue)
            else:
                log_and_print("Unable to fetch issue information: " + issue, "ERROR")
            
        log_and_print("***" + issue + "*** - Downloading Done")
        log_and_print("\n")


def log_and_print(content, type="INFO"):
    print content
    if type == "INFO":
        logging.info(content)
    elif type == "ERROR":
        logging.error(content)
    elif type == "WARNING":
        logging.warning(content)


issues_fetched = 0
total_issues = 0


if __name__ == "__main__":
    init_logging()
    global issues_fetched, total_issues
    try:
        issues = jira_inst.search_issues(JQL, 0)
        log_and_print("For the JQL - " + JQL)
        total_issues = issues.total
        log_and_print("Total number of issues: " + str(total_issues))
        cont = raw_input("Continue? (y/n) :")
        if cont.lower() == "y":
            startAt = int(raw_input("Start at? (Default: 0) :"))
            while startAt + issues_fetched < total_issues:
                issues = jira_inst.search_issues(JQL, startAt + issues_fetched)
                fetch_issues_from_jql(issues)
    except Exception as ex:
        log_and_print("ERROR: " + str(ex), "ERROR")
    finally:
        log_and_print("Shutting Down!")
        log_and_print("Details before shut down")
        log_and_print("Started At: " + str(startAt))
        log_and_print("issues_fetched: " + str(issues_fetched))
        log_and_print("total_issues: " + str(total_issues))
        log_and_print("*** END ***")
