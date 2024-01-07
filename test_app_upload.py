import google_auth_httplib2
import httplib2
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SHEET_ID = "1vXaglvGGbGN0pc8vEjiA7bCPpPTacFxvLGm3iKRVVUw"
SHEET_NAME = "シート1"

@st.experimental_singleton()
def connect_to_gsheet():
    # Create a connection object
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=[SCOPE]
    )

    # Create a new Http() object for every request
    def build_request(http, *args, **kwargs):
        new_http = google_auth_httplib2.AuthorizedHttp(
            credentials, http=httplib2.Http()
        )

        return HttpRequest(new_http, *args, **kwargs)

    authorized_http = google_auth_httplib2.AuthorizedHttp(
        credentials, http=httplib2.Http()
    )

    service = build("sheets", "v4", requestBuilder=build_request, http=authorized_http)
    gsheet_connector = service.spreadsheets()

    return gsheet_connector


def add_row_to_gsheet(gsheet_connector, row):
    gsheet_connector.values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A:C",
        body=dict(values=row),
        valueInputOption="USER_ENTERED",
    ).execute()

#### main contents
st.title("Hello")

gsheet_connector = connect_to_gsheet()

form = st.form(key="test")
with form:
    text1 = st.text_input("first")
    text2 = st.text_input("second")
    submitted = st.form_submit_button(label="Submit")

if submitted:
    add_row_to_gsheet(gsheet_connector, [[text1, text2]])
    st.success("OK!")
