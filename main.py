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
st.set_page_config(
    layout="wide",
    page_title="Figma Design to Test Cases"
)

# Azure OpenAI setup
OPENAI_API_VERSION = "2024-02-15-preview"
OPENAI_API_ENDPOINT = "https://disprz-originals.openai.azure.com/"
OPENAI_API_KEY = "1dfeeaf8f4e945e5a461f82fd08169b3"

# Function to encode image to base64
def encode_image(image_path):
    """
    Encodes an image to a base64 string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

class testcaseitems(BaseModel):
    Name: str = Field(..., alias='Name', description='Name of the test case, can be appened with a sample testcaseID like TC001, example name:TC001_User Creation Validation')
    Status: str = Field(..., alias='Status', description='Status')
    Precondition: str = Field(..., alias='Precondition', description='Precondition')
    Objective: str = Field(..., alias='Objective', description='Objective')
    Priority: str = Field(..., alias='Priority', description='Priority')
    AutomationCoverage: str = Field(..., alias='AutomationCoverage', description='AutomationCoverage')
    AutomationType: str = Field(..., alias='AutomationType', description='AutomationType')
    TestScriptStep: str = Field(..., alias='TestScriptStep', description='TestScript (Step-by-Step) - Step')
    TestScriptTestData: str = Field(..., alias='TestScriptTestData', description='Test Script (Step-by-Step) - Test Data')
    TestScriptExpectedResult: str = Field(..., alias='TestScriptExpectedResult', description='Test Script (Step-by-Step) - Expected Result')
    TestScriptPlainText: str = Field(..., alias='TestScriptPlainText', description='Test Script (Plain Text)')
    
class ExtractedInfo(BaseModel):
    testcases: List[testcaseitems] = Field(..., description='Give the test cases in sequence')


# Function to send request with image
# Function to send request with image
def send_request_with_image(base64_image, your_prompt):
    """
    Sends a prompt and an image (as base64) to the GPT model.
    """
    client = AzureOpenAI(
        api_version=OPENAI_API_VERSION,
        azure_endpoint=OPENAI_API_ENDPOINT,
        api_key=OPENAI_API_KEY
    )

    content = [
        {"type": "text", "text": your_prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    ]

    messages = [
        {"role": "system", "content": "You are an assistant that converts a figma screen into test cases."},
        {"role": "user", "content": content}
    ]

    # Send the request to GPT
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

# Streamlit app
def main():
    st.markdown(
        '<div style="text-align: center; margin-top: -55px; "><img src="./app/static/disprz_reverse.png" width="200"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="text-align: center; font-family: 'Source Sans Pro', sans-serif; font-size: 30px; font-weight: 650; margin-bottom: 15px; margin-top: -10px;">
        ✨ Figma Design to Test Cases ✨
        </div>
        """,
        unsafe_allow_html=True,
    )
    container2 = st.container(border=True)
    container2.write("Upload Figma Design to Generate Testcases")

    uploaded_file = container2.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        st.session_state["uploaded_image"] = uploaded_file.read()
        base64_image = base64.b64encode(st.session_state["uploaded_image"]).decode('utf-8')
        container2.markdown(
                f"""
                <div style="text-align: center;">
                    <img src="data:image/jpeg;base64,{base64_image}" alt="Uploaded Image" style="width:700px;height:300px;"/>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Get prompt input from user
    
    
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

# Render the text area
    user_answer = container2.text_area("", placeholder="Additional Prompts (Optional)", height=2)
    if user_answer:
            your_prompt =  "Generate the testcases in json format for the figma image uploaded, The json must be having the following keys: Name,Status,Precondition, Objective,Priority, Automation Coverage,Automation Type,TestScript (Step-by-Step) - Step,Test Script (Step-by-Step) - Test Data, Test Script (Step-by-Step) - Expected Result,Test Script (Plain Text)." + str(user_answer)
    else:
            your_prompt =  "Generate the testcases in json format for the figma image uploaded, The json must be having the following keys: Name,Status,Precondition, Objective,Priority, Automation Coverage,Automation Type,TestScript (Step-by-Step) - Step,Test Script (Step-by-Step) - Test Data, Test Script (Step-by-Step) - Expected Result,Test Script (Plain Text)."


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
                    # Button to submit the answer

    button2=container2.button("Generate Testcases", type="primary", use_container_width=True)
    if button2:
        try:
            response = send_request_with_image(base64_image, your_prompt)
            container3=st.container(border=True)
            container3.subheader("Generated Testcases")
            df = pd.DataFrame(response)
            df.columns = [
                    "Name", "Status", "Precondition", "Objective", "Priority", "Automation Coverage", 
                    "Automation Type", "TestScript (Step-by-Step) - Step", 
                    "Test Script (Step-by-Step) - Test Data", 
                    "Test Script (Step-by-Step) - Expected Result", "Test Script (Plain Text)"
                ]

            container3.dataframe(df)

            csv_data = df.to_csv(index=False)
            b64 = base64.b64encode(csv_data.encode()).decode()
            download_button_html = f"""
                    <div style="display: flex; justify-content: center;">
                        <a href="data:file/csv;base64,{b64}" download="test_cases.csv">
                            <button style="background-color: #FFEA00; color: black; padding: 10px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px;">Download as CSV</button>
                        </a>
                    </div>
                """
            container3.markdown(download_button_html, unsafe_allow_html=True)
            deploy_button_html = """
                    <div style="display: flex; justify-content: center; margin-top: 10px;">
                        <button style="background-color: #49d649; color: black; padding: 10px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px;" disabled>Deploy to Zepher</button>
                    </div>
                """
            container3.markdown(deploy_button_html, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
