import streamlit as st
import os
import base64
from openai import AzureOpenAI
from pydantic import BaseModel
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from typing import List
import json
import pandas as pd
from PIL import Image
import time
import requests
st.set_page_config(
    layout="wide",
    page_title="Figma Design to Test Cases"
)

OPENAI_API_VERSION = "2024-02-15-preview"
OPENAI_API_ENDPOINT = "https://disprz-originals.openai.azure.com/"
OPENAI_API_KEY = "1dfeeaf8f4e945e5a461f82fd08169b3"

def encode_image(image_path):
    """
    Encodes an image to a base64 string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

class TestScriptStep(BaseModel):
    TestScriptStepName: str = Field(..., alias='TestScriptStepName', description='Step name for the test script should be a actual name, do not name it Step 1')
    TestScriptTestData: str = Field(..., alias='TestScriptTestData', description='Test data used for this step')
    TestScriptExpectedResult: str = Field(..., alias='TestScriptExpectedResult', description='Expected result for this step')
    TestScriptPlainText: str = Field(..., alias='TestScriptPlainText', description='Plain text description of the step')

class testcaseitems(BaseModel):
    Name: str = Field(..., alias='Name', description='Name of the test case, can be appened with a sample testcaseID like TC001, example name:TC001_User Creation Validation')
    Status: str = Field(..., alias='Status', description='Status, Should be (Draft, Deprecated, Approved)')
    Precondition: str = Field(..., alias='Precondition', description='Precondition')
    Objective: str = Field(..., alias='Objective', description='Objective')
    Priority: str = Field(..., alias='Priority', description='Priority, Should be (High, Normal or Low)')
    AutomationCoverage: str = Field(..., alias='AutomationCoverage', description='AutomationCoverage')
    AutomationType: str = Field(..., alias='AutomationType', description='AutomationType')
    TestScriptSteps: List[TestScriptStep] = Field(..., alias='TestScriptSteps', description='List of test script steps')

class ExtractedInfo(BaseModel):
    testcases: List[testcaseitems] = Field(..., description='Give the test cases in sequence')


def send_request_with_image(base64_images, your_prompt):
    """
    Sends a prompt and an image (as base64) to the GPT model.
    """
    client = AzureOpenAI(
        api_version=OPENAI_API_VERSION,
        azure_endpoint=OPENAI_API_ENDPOINT,
        api_key=OPENAI_API_KEY
    )

    content = [{"type": "text", "text": your_prompt}]
    for img in base64_images:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
    

    messages = [
        {"role": "system", "content": "You are an assistant that converts a figma screen into test cases."},
        {"role": "user", "content": content}
    ]

    response = client.chat.completions.create(
        model="GPT4o",
        messages=messages,
        temperature=0.5,functions=[
                {
                    "name": "Test_Cases_Generator",
                    "parameters": ExtractedInfo.model_json_schema()
                }
            ],
        function_call={"name":"Test_Cases_Generator"})
    
    response=response.choices[0].message.function_call.arguments
    print(response)
    test_cases = json.loads(response)
    return test_cases['testcases']

@st.dialog("Deploy to Zepher")
def deploytozepher(response):
    user_answer=st.text_area("Enter the folder name")
    
    if st.button("Submit"):
        API_BASE_URL = "https://api.zephyrscale.smartbear.com/v2"
        TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb250ZXh0Ijp7ImJhc2VVcmwiOiJodHRwczovL2Rpc3Byei5hdGxhc3NpYW4ubmV0IiwidXNlciI6eyJhY2NvdW50SWQiOiI2MjAwYjYzZGU1Y2FmZjAwNzBlMTczMTQiLCJ0b2tlbklkIjoiY2I1YWU0MDgtMWM3MC00YjAyLTgxOGUtYjliNTMzNThlMTVlIn19LCJpc3MiOiJjb20ua2Fub2FoLnRlc3QtbWFuYWdlciIsInN1YiI6IjczYTFjODVkLTgzOWYtM2M5YS1iYjY0LWQyMTNjMjQyNGUzMCIsImV4cCI6MTc3MDk4NzMwNywiaWF0IjoxNzM5NDUxMzA3fQ.nQhb6cSv-upA-1uueA_EPQycqaI3OapFu65u9_Gooq8"
        PROJECT_KEY = "DIS" 
        PARENT_FOLDER_ID = 20770497

        # Headers
        HEADERS = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }


        def create_subfolder(folder_name):
            """Create a subfolder inside the specified folder."""
            url = f"{API_BASE_URL}/folders"
            payload = {
                "name": folder_name,
                "parentId": PARENT_FOLDER_ID,  # Ensure this is the correct parent folder ID
                "projectKey": PROJECT_KEY,
                "folderType": "TEST_CASE"
            }

            response = requests.post(url, headers=HEADERS, json=payload)
            if response.status_code == 201:
                subfolder_id = response.json().get("id")
                print(f"Subfolder '{folder_name}' created successfully with ID: {subfolder_id}")
                return subfolder_id
            else:
                print(f"Failed to create subfolder: {response.status_code} - {response.text}")
                return None

        def upload_test_cases_from_json(response, folder_id):
            """Upload test cases from JSON and manage test steps correctly."""
            create_url = f"{API_BASE_URL}/testcases"
            steps_url_template = f"{API_BASE_URL}/testcases/{{test_case_id}}/teststeps"

            for test_case in response:
                # Step 1: Create the test case
                payload = {
                    "projectKey": PROJECT_KEY,
                    "name": test_case["Name"],
                    "statusName": test_case.get("Status", "Draft"),
                    "precondition": test_case.get("Precondition", ""),
                    "objective": test_case.get("Objective", ""),
                    "priorityName": test_case.get("Priority", "Normal"),
                    "folderId": folder_id,
                    "customFields": {
                        "Automation Coverage": "Not Applicable",
                        "Automation Type": "Yet To Start"
                    }
                }

                response = requests.post(create_url, headers=HEADERS, json=payload)
                if response.status_code == 201:
                    test_case_id = response.json().get("key")
                    print(f"Test case '{test_case['Name']}' created successfully with ID: {test_case_id}")

                    # Step 2: Overwrite the default placeholder step with the first step
                    steps_url = steps_url_template.format(test_case_id=test_case_id)
                    test_steps = test_case.get("TestScriptSteps", [])
                    if test_steps:
                        first_step = test_steps[0]
                        overwrite_payload = {
                            "mode": "OVERWRITE",
                            "items": [
                                {
                                    "inline": {
                                        "description": first_step.get("TestScriptStepName", ""),
                                        "testData": first_step.get("TestScriptTestData", ""),
                                        "expectedResult": first_step.get("TestScriptExpectedResult", "")
                                    }
                                }
                            ]
                        }

                        overwrite_response = requests.post(steps_url, headers=HEADERS, json=overwrite_payload)
                        if overwrite_response.status_code == 201:
                            print(f"Initial test step overwritten successfully for test case ID: {test_case_id}")
                        else:
                            print(f"Failed to overwrite initial test step: {overwrite_response.status_code} - {overwrite_response.text}")

                        # Step 3: Append subsequent steps if available
                        additional_steps = []
                        for step in test_steps[1:]:
                            additional_steps.append({
                                "inline": {
                                    "description": step.get("TestScriptStepName", ""),
                                    "testData": step.get("TestScriptTestData", ""),
                                    "expectedResult": step.get("TestScriptExpectedResult", "")
                                }
                            })

                        if additional_steps:
                            append_payload = {
                                "mode": "APPEND",
                                "items": additional_steps
                            }
                            append_response = requests.post(steps_url, headers=HEADERS, json=append_payload)
                            if append_response.status_code == 201:
                                print(f"Additional steps appended for test case ID: {test_case_id}")
                            else:
                                print(f"Failed to append steps: {append_response.status_code} - {append_response.text}")

                    else:
                        print(f"No steps found for test case '{test_case['Name']}'")

                    time.sleep(1) 

                else:
                    print(f"Failed to create test case '{test_case['Name']}': {response.status_code} - {response.text}")




        subfolder_name = user_answer
        subfolder_id = create_subfolder(subfolder_name)
        upload_test_cases_from_json(response, subfolder_id)
        st.rerun()

def main():
    st.markdown(
        """
        <div style="text-align: center; font-family: 'Source Sans Pro', sans-serif; font-size: 30px; font-weight: 650; margin-bottom: 15px; margin-top: -10px;">
        🎨 Figma Design to Test Cases 💻
        </div>
        """,
        unsafe_allow_html=True,
    )
    container2 = st.container(border=True)
    container2.write("Upload Figma Design to Generate Testcases")

    uploaded_files = container2.file_uploader("Upload images (up to 3)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        base64_images = []
        for uploaded_file in uploaded_files:
            base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
            base64_images.append(base64_image)

        if len(base64_images) == 1:
            container2.markdown(f"""
            <div style="text-align: center;">
                <img src="data:image/jpeg;base64,{base64_images[0]}" alt="Uploaded Image" style="width:700px;height:300px;"/>
            </div>
            """, unsafe_allow_html=True)
        else:
            cols = container2.columns(len(base64_images))
            for i, image in enumerate(base64_images):
                with cols[i]:
                    st.markdown(f"""
                    <div style="text-align: center;">
                        <img src="data:image/jpeg;base64,{image}" alt="Uploaded Image" style="width:700px;height:300px;"/>
                    </div>
                    """, unsafe_allow_html=True)

    
    
    st.markdown(
    """
    <style>
    /* Target the Streamlit text area */
    div[data-testid="stTextArea"] {
        margin-top: 5px; /* Remove or reduce top margin */
    }

    /* Optional: Add padding to the text area itself */
    textarea {
        padding: 10px; /* Adjust padding inside the text area */
        border: 1px solid #ccc; /* Optional: Customize the border */
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

    user_answer = container2.text_area("", placeholder="Additional Prompts (Optional)", height=68)
    if user_answer:
            your_prompt =  "Generate the testcases in json format for the figma image uploaded, The json must be having the following keys: Name,Status,Precondition, Objective,Priority, Automation Coverage,Automation Type,TestScriptData. Generate a minimum of 10 test cases and a mximum of 30 testcases." + str(user_answer)
    else:
            your_prompt =  "Generate the testcases in json format for the figma image uploaded, The json must be having the following keys: Name,Status,Precondition, Objective,Priority, Automation Coverage,Automation Type,TestScriptData.Generate a minimum of 10 test cases and a mximum of 30 testcases."


    container2.markdown(
                        """
                        <style>
        button[kind="primary"] {
        display: block;
        font-family: 'Source Sans Pro', sans-serif;
        width: 250px;
        height: 50px;
        padding: 8px;
        background-color: #40E0D0; /* Turquoise Green */
        color: black;
        border: none;
        border-radius: 5px;
        font-size: 16px;
        font-weight: bold; /* Bold text */
        text-align: center;
        cursor: pointer;
        margin: 0 auto; /* Center the button horizontally */
        margin-top: -5px;
    }
                        </style>
                        """, unsafe_allow_html=True
                    )
                    

    button2=container2.button("Generate Testcases", type="primary", use_container_width=True, key="Hi")
    if button2:
        try:
            response = send_request_with_image(base64_images, your_prompt)
            container3=st.container(border=True)
            container3.subheader("Generated Testcases")
            rows = []
            st.session_state['response']=response
            for testcase in response:
                step_names = '\n'.join([f"{idx+1}. {step['TestScriptStepName']}" for idx, step in enumerate(testcase['TestScriptSteps'])])
                test_data = '\n'.join([f"{idx+1}. {step['TestScriptTestData']}" for idx, step in enumerate(testcase['TestScriptSteps'])])
                expected_results = '\n'.join([f"{idx+1}. {step['TestScriptExpectedResult']}" for idx, step in enumerate(testcase['TestScriptSteps'])])
                plain_texts = '\n'.join([f"{idx+1}. {step['TestScriptPlainText']}" for idx, step in enumerate(testcase['TestScriptSteps'])])

                rows.append({
                    "Name": testcase['Name'],
                    "Status": testcase['Status'],
                    "Precondition": testcase['Precondition'],
                    "Objective": testcase['Objective'],
                    "Priority": testcase['Priority'],
                    "Automation Coverage": testcase['AutomationCoverage'],
                    "Automation Type": testcase['AutomationType'],
                    "TestScript (Step-by-Step) - Step": step_names,
                    "Test Script (Step-by-Step) - Test Data": test_data,
                    "Test Script (Step-by-Step) - Expected Result": expected_results,
                    "Test Script (Plain Text)": plain_texts
                })
            df = pd.DataFrame(rows)
            df.columns = [
                        "Name", "Status", "Precondition", "Objective", "Priority", "Automation Coverage", 
                        "Automation Type", "TestScript (Step-by-Step) - Step", "Test Script (Step-by-Step) - Test Data", 
                        "Test Script (Step-by-Step) - Expected Result", "Test Script (Plain Text)"
                    ]

            container3.dataframe(df)
            st.session_state['df'] = df
            st.session_state['csv_data'] = df.to_csv(index=False)
            b64 = base64.b64encode(st.session_state['csv_data'].encode()).decode()
            download_button_html = f"""
                    <div style="display: flex; justify-content: center;">
                        <a href="data:file/csv;base64,{b64}" download="test_cases.csv">
                            <button style="background-color: #FFEA00; color: black; padding: 10px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px;">Download as CSV</button>
                        </a>
                    </div>
                """
            container3.markdown(download_button_html, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")

def main2():
    if 'response' in st.session_state:
        if st.button("Deploy to Zepher", type="primary", use_container_width=True, key="Hello"):
            deploytozepher(st.session_state['response'])
            st.session_state.pop('response', None)

if __name__ == "__main__":
    main()
    main2()